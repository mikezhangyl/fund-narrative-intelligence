from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scanners.backup_restore_archive import (
    build_backup_restore_archive_manifest,
    render_backup_restore_archive_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a portable local backup/restore archive.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "config" / "backup_restore_archive_input.json")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs" / "backup_restore_archive" / "current")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = _read_json(args.input)
    include_paths = [_resolve_path(args.project_root, item) for item in _list(payload.get("include_paths"))]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_backup_restore_archive_manifest(
        project_root=args.project_root,
        include_paths=include_paths,
        release_metadata=_mapping(payload.get("release_metadata")),
    )
    zip_path = args.output_dir / "backup_restore_archive.zip"
    _write_zip(zip_path=zip_path, project_root=args.project_root, manifest=manifest)
    manifest["archive"]["zip_path"] = str(zip_path)
    json_path = args.output_dir / "backup_restore_archive_manifest.json"
    html_path = args.output_dir / "backup_restore_archive.html"
    _write_json(json_path, manifest)
    html_path.write_text(render_backup_restore_archive_html(manifest), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "json_path": str(json_path),
                "html_path": str(html_path),
                "zip_path": str(zip_path),
                "included_file_count": manifest["summary"]["included_file_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_zip(*, zip_path: Path, project_root: Path, manifest: dict[str, Any]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in manifest["included_files"]:
            relative = item["path"]
            archive.write(project_root / relative, arcname=relative)


def _resolve_path(project_root: Path, path: Any) -> Path:
    resolved = Path(str(path))
    if resolved.is_absolute():
        return resolved
    return project_root / resolved


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
