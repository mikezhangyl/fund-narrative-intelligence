from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from src.modules.narrative_review.preview import build_review_action_preview
from src.validation import (
    validate_registry_payload,
    validate_review_action_preview_payload,
)


def persist_review_action_registry(
    *,
    registry_path: Path,
    action_path: Path,
    registry_output_path: Path,
    allow_registry_overwrite: bool = False,
    allow_output_overwrite: bool = False,
) -> dict[str, Any]:
    registry_file = _resolve_existing_file(registry_path, "registry_path")
    action_file = _resolve_existing_file(action_path, "action_path")
    output_path = registry_output_path.expanduser().resolve(strict=False)
    _validate_registry_output_path(
        output_path=output_path,
        registry_file=registry_file,
        action_file=action_file,
        allow_registry_overwrite=allow_registry_overwrite,
        allow_output_overwrite=allow_output_overwrite,
    )

    registry_payload = _read_json_object(registry_file)
    action_payload = _read_json_object(action_file)
    preview = build_review_action_preview(registry_payload, action_payload)
    validate_review_action_preview_payload(preview)
    result_registry = preview["result_registry"]
    validate_registry_payload(result_registry)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomically(result_registry, output_path)
    return {
        "version": "review-action-persistence-result-v1",
        "status": "persisted",
        "action_id": action_payload["action_id"],
        "candidate_narrative_id": action_payload["candidate_narrative_id"],
        "registry_path": str(registry_file),
        "registry_output_path": str(output_path),
        "registry_overwritten": output_path == registry_file,
        "registry_delta": preview["registry_delta"],
    }


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


def _validate_registry_output_path(
    *,
    output_path: Path,
    registry_file: Path,
    action_file: Path,
    allow_registry_overwrite: bool,
    allow_output_overwrite: bool,
) -> None:
    if output_path == action_file:
        raise ValueError("registry output must not overwrite action input")
    legacy_temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    if legacy_temporary_path in {registry_file, action_file}:
        raise ValueError("temporary output path must not collide with source inputs")
    if output_path == registry_file and not allow_registry_overwrite:
        raise ValueError(
            "in-place registry persistence requires allow_registry_overwrite"
        )
    if output_path.exists() and output_path.is_dir():
        raise ValueError("registry output must not be a directory")
    if (
        output_path.exists()
        and output_path != registry_file
        and not allow_output_overwrite
    ):
        raise ValueError("registry output already exists")


def _write_json_atomically(payload: dict[str, Any], output_path: Path) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    with open(descriptor, "w", encoding="utf-8") as temporary_file:
        temporary_file.write(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        )
    temporary_path.replace(output_path)
