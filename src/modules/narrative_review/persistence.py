from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from src.modules.narrative_review.preview import build_review_action_preview
from src.validation import (
    validate_registry_payload,
    validate_review_action_persistence_result_payload,
    validate_review_action_preview_payload,
)


def persist_review_action_registry(
    *,
    registry_path: Path,
    action_path: Path,
    registry_output_path: Path,
    result_output_path: Path | None = None,
    result_output_dir: Path | None = None,
    allow_registry_overwrite: bool = False,
    allow_output_overwrite: bool = False,
    allow_result_overwrite: bool = False,
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
    if result_output_path is None and result_output_dir is None:
        raise ValueError("persistence result output path or directory is required")

    registry_payload = _read_json_object(registry_file)
    action_payload = _read_json_object(action_file)
    preview = build_review_action_preview(registry_payload, action_payload)
    validate_review_action_preview_payload(preview)
    result_registry = preview["result_registry"]
    validate_registry_payload(result_registry)
    resolved_result_output_path = _resolve_result_output_path(
        action_id=action_payload["action_id"],
        result_output_path=result_output_path,
        result_output_dir=result_output_dir,
    )
    if resolved_result_output_path is not None:
        _validate_result_output_path(
            result_output_path=resolved_result_output_path,
            registry_file=registry_file,
            action_file=action_file,
            registry_output_path=output_path,
            allow_result_overwrite=allow_result_overwrite,
        )

    result = {
        "version": "review-action-persistence-result-v1",
        "status": "persisted",
        "action_id": action_payload["action_id"],
        "candidate_narrative_id": action_payload["candidate_narrative_id"],
        "registry_path": str(registry_file),
        "registry_output_path": str(output_path),
        "registry_overwritten": _path_key(output_path) == _path_key(registry_file),
        "overwrite_policy": {
            "allow_registry_overwrite": allow_registry_overwrite,
            "allow_output_overwrite": allow_output_overwrite,
            "allow_result_overwrite": allow_result_overwrite,
        },
        "registry_delta": preview["registry_delta"],
    }
    if resolved_result_output_path is not None:
        result = {
            **result,
            "persistence_result_path": str(resolved_result_output_path),
        }
    validate_review_action_persistence_result_payload(result)
    _write_registry_and_result(
        registry_payload=result_registry,
        registry_output_path=output_path,
        result_payload=result,
        result_output_path=resolved_result_output_path,
    )
    return result


def _write_registry_and_result(
    *,
    registry_payload: dict[str, Any],
    registry_output_path: Path,
    result_payload: dict[str, Any],
    result_output_path: Path | None,
) -> None:
    registry_existed = registry_output_path.exists()
    registry_backup = _backup_existing_file(registry_output_path)
    result_existed = result_output_path.exists() if result_output_path else False
    result_backup = (
        _backup_existing_file(result_output_path) if result_output_path else None
    )
    try:
        registry_output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomically(registry_payload, registry_output_path)
        if result_output_path is not None:
            result_output_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json_atomically(result_payload, result_output_path)
    except Exception:
        _restore_or_remove(registry_output_path, registry_backup, registry_existed)
        if result_output_path is not None:
            _restore_or_remove(result_output_path, result_backup, result_existed)
        raise
    else:
        _remove_if_exists(registry_backup)
        _remove_if_exists(result_backup)


def _backup_existing_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    descriptor, backup_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.backup.",
        suffix=".tmp",
    )
    os.close(descriptor)
    Path(backup_name).unlink()
    path.replace(backup_name)
    return Path(backup_name)


def _restore_or_remove(path: Path, backup_path: Path | None, existed: bool) -> None:
    if path.exists():
        path.unlink()
    if existed and backup_path is not None and backup_path.exists():
        backup_path.replace(path)
    elif backup_path is not None:
        _remove_if_exists(backup_path)


def _remove_if_exists(path: Path | None) -> None:
    if path is not None and path.exists():
        path.unlink()


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
    if _path_key(output_path) == _path_key(action_file):
        raise ValueError("registry output must not overwrite action input")
    legacy_temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    source_keys = {_path_key(registry_file), _path_key(action_file)}
    if _path_key(legacy_temporary_path) in source_keys:
        raise ValueError("temporary output path must not collide with source inputs")
    if _path_key(output_path) == _path_key(registry_file) and not allow_registry_overwrite:
        raise ValueError(
            "in-place registry persistence requires allow_registry_overwrite"
        )
    if output_path.exists() and output_path.is_dir():
        raise ValueError("registry output must not be a directory")
    if (
        output_path.exists()
        and _path_key(output_path) != _path_key(registry_file)
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


def _resolve_result_output_path(
    *,
    action_id: str,
    result_output_path: Path | None,
    result_output_dir: Path | None,
) -> Path | None:
    if result_output_path is None and result_output_dir is None:
        return None
    output_dir = result_output_dir or Path(".")
    if result_output_path is None:
        return _default_result_output_path(output_dir, action_id).resolve(strict=False)
    expanded = result_output_path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve(strict=False)
    return (output_dir / expanded).resolve(strict=False)


def _default_result_output_path(output_dir: Path, action_id: str) -> Path:
    safe_action_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", action_id)
    return (
        output_dir.expanduser()
        / f"candidate_review_action_{safe_action_id}_persistence.json"
    )


def _validate_result_output_path(
    *,
    result_output_path: Path,
    registry_file: Path,
    action_file: Path,
    registry_output_path: Path,
    allow_result_overwrite: bool,
) -> None:
    blocked_keys = {
        _path_key(registry_file),
        _path_key(action_file),
        _path_key(registry_output_path),
    }
    if _path_key(result_output_path) in blocked_keys:
        raise ValueError(
            "persistence result output must not overwrite registry, action, or registry output"
        )
    if result_output_path.exists() and result_output_path.is_dir():
        raise ValueError("persistence result output must not be a directory")
    if result_output_path.exists() and not allow_result_overwrite:
        raise ValueError("persistence result output already exists")


def _path_key(path: Path) -> str:
    return str(path.resolve(strict=False)).casefold()
