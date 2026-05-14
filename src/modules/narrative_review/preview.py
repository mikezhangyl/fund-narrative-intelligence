from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.modules.narrative_review.promotion import apply_candidate_review_action
from src.modules.snapshot_writer.writer import write_json_artifact
from src.validation import validate_review_action_preview_payload


def build_review_action_preview(
    registry_payload: dict[str, Any],
    action_payload: dict[str, Any],
) -> dict[str, Any]:
    """Apply a review action to a registry copy and return a web-ready preview."""
    original_registry = deepcopy(registry_payload)
    result_registry = apply_candidate_review_action(registry_payload, action_payload)
    reviewed_candidate = _find_candidate(
        result_registry["candidate_narratives"],
        action_payload["candidate_narrative_id"],
    )
    original_candidate = _find_candidate(
        original_registry["candidate_narratives"],
        action_payload["candidate_narrative_id"],
    )
    return {
        "version": "candidate-review-action-preview-v1",
        "status": "previewed",
        "source_registry_mutated": registry_payload != original_registry,
        "action": deepcopy(action_payload),
        "summary": {
            "action": action_payload["action"],
            "candidate_narrative_id": action_payload["candidate_narrative_id"],
            "candidate_status_after": reviewed_candidate["status"],
            "human_review_status_after": reviewed_candidate["human_review_status"],
            "active_narrative_count_before": len(original_registry["narratives"]),
            "active_narrative_count_after": len(result_registry["narratives"]),
            "promotion_target_id": reviewed_candidate.get("promotion_target_id"),
            "source_registry_written": False,
            "requires_explicit_persistence_step": True,
        },
        "registry_delta": _registry_delta(
            original_registry=original_registry,
            result_registry=result_registry,
            original_candidate=original_candidate,
            reviewed_candidate=reviewed_candidate,
        ),
        "result_registry": result_registry,
    }


def write_review_action_preview(
    *,
    registry_path: Path,
    action_path: Path,
    output_dir: Path,
    output_path: Path | None = None,
) -> Path:
    registry_file = _resolve_existing_file(registry_path, "registry_path")
    action_file = _resolve_existing_file(action_path, "action_path")
    registry_payload = _read_json_object(registry_file)
    action_payload = _read_json_object(action_file)
    preview = build_review_action_preview(registry_payload, action_payload)
    output_root = output_dir.expanduser().resolve(strict=False)
    path = _resolve_output_path(
        output_root=output_root,
        action_id=action_payload["action_id"],
        output_path=output_path,
    )
    _validate_output_path(path, output_root, registry_file, action_file)
    validate_review_action_preview_payload(preview)
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_json_artifact(preview, path)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve_existing_file(path: Path, context: str) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if not resolved.exists():
        raise ValueError(f"{context} does not exist: {path}")
    if not resolved.is_file():
        raise ValueError(f"{context} must be a file: {path}")
    return resolved


def _resolve_output_path(
    *,
    output_root: Path,
    action_id: str,
    output_path: Path | None,
) -> Path:
    if output_path is None:
        return _default_output_path(output_root, action_id)
    expanded = output_path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve(strict=False)
    return (output_root / expanded).resolve(strict=False)


def _default_output_path(output_root: Path, action_id: str) -> Path:
    safe_action_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", action_id)
    return output_root / f"candidate_review_action_{safe_action_id}_preview.json"


def _validate_output_path(
    output_path: Path,
    output_root: Path,
    registry_file: Path,
    action_file: Path,
) -> None:
    if not output_path.is_relative_to(output_root):
        raise ValueError("review action output must stay inside output_dir")
    if output_path in {registry_file, action_file}:
        raise ValueError("review action output must not overwrite registry or action input")


def _registry_delta(
    *,
    original_registry: dict[str, Any],
    result_registry: dict[str, Any],
    original_candidate: dict[str, Any],
    reviewed_candidate: dict[str, Any],
) -> dict[str, Any]:
    original_narrative_ids = {
        narrative["narrative_id"] for narrative in original_registry["narratives"]
    }
    result_narrative_ids = [
        narrative["narrative_id"] for narrative in result_registry["narratives"]
    ]
    added_ids = [
        narrative_id
        for narrative_id in result_narrative_ids
        if narrative_id not in original_narrative_ids
    ]
    return {
        "active_narrative_ids_added": added_ids,
        "active_narrative_count_change": (
            len(result_registry["narratives"]) - len(original_registry["narratives"])
        ),
        "candidate_changes": {
            "candidate_narrative_id": reviewed_candidate["candidate_narrative_id"],
            "before": _candidate_review_projection(original_candidate),
            "after": _candidate_review_projection(reviewed_candidate),
        },
    }


def _candidate_review_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": candidate.get("status"),
        "human_review_status": candidate.get("human_review_status"),
        "reviewed_by": candidate.get("reviewed_by"),
        "reviewed_at": candidate.get("reviewed_at"),
        "promotion_target_id": candidate.get("promotion_target_id"),
    }


def _find_candidate(
    candidates: list[dict[str, Any]],
    candidate_id: str,
) -> dict[str, Any]:
    for candidate in candidates:
        if candidate["candidate_narrative_id"] == candidate_id:
            return candidate
    raise ValueError(f"candidate missing after preview: {candidate_id}")
