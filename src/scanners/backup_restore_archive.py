from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

SECRET_PATH_MARKERS = (".env", "secret", "token", "credential", "cache", "log")


def build_backup_restore_archive_manifest(
    *,
    project_root: Path,
    include_paths: list[Path],
    release_metadata: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    included, excluded = _partition_paths(project_root=project_root, include_paths=include_paths)
    return {
        "version": "backup-restore-archive-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "included_file_count": len(included),
            "excluded_file_count": len(excluded),
            "warning_count": 0,
        },
        "release_metadata": release_metadata or {},
        "included_files": included,
        "excluded_files": excluded,
        "integrity_manifest": {
            "algorithm": "sha256",
            "files": [
                {"path": item["path"], "checksum_sha256": item["checksum_sha256"]}
                for item in included
            ],
        },
        "restore_contract": {
            "compatibility_version": "backup-restore-archive-v1",
            "restore_validation_required": True,
            "rollback_supported": True,
            "current_state_overwrite_allowed_without_validation": False,
        },
        "archive": {
            "format": "zip",
            "zip_path": "",
        },
    }


def render_backup_restore_archive_html(manifest: dict[str, Any]) -> str:
    summary = _mapping(manifest.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>备份恢复与便携发布归档</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>备份恢复与便携发布归档</h1>",
            '<section class="summary">',
            _html_kv("包含文件", summary.get("included_file_count", 0)),
            _html_kv("排除文件", summary.get("excluded_file_count", 0)),
            "<p>恢复前必须完成完整性校验；归档不包含 secret、token、本地环境或缓存日志路径。</p>",
            "</section>",
            _files_table(_list(manifest.get("included_files"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _partition_paths(*, project_root: Path, include_paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for path in sorted({Path(item) for item in include_paths}, key=lambda item: str(item)):
        relative = _relative_path(project_root, path)
        if _is_excluded(relative):
            excluded.append({"path": relative, "reason": "secret_or_local_environment_path"})
            continue
        if not path.exists() or not path.is_file():
            excluded.append({"path": relative, "reason": "missing_or_not_file"})
            continue
        data = path.read_bytes()
        included.append(
            {
                "path": relative,
                "size_bytes": len(data),
                "checksum_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return included, excluded


def _relative_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_excluded(relative_path: str) -> bool:
    lowered = relative_path.casefold()
    return any(marker in lowered for marker in SECRET_PATH_MARKERS)


def _files_table(files: list[Any]) -> str:
    rows = [_mapping(file) for file in files]
    if not rows:
        return "<section><h2>完整性校验</h2><p>没有归档文件。</p></section>"
    header = "".join(_th(label) for label in ("路径", "大小", "SHA256"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('path'))}</td>"
        f"<td>{_html_text(row.get('size_bytes'))}</td>"
        f"<td>{_html_text(row.get('checksum_sha256'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>完整性校验</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _th(label: str) -> str:
    return f"<th>{_html_text(label)}</th>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #edf0f5; padding: 10px 12px; text-align: left; vertical-align: top; }
th { background: #eef2f7; font-size: 13px; }
td { font-size: 13px; }
""".strip()
