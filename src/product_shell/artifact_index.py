from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from html import escape
from pathlib import Path
from typing import Any

SENSITIVE_PATH_PARTS = ("secret", "token", "password", "credential", "api_key", ".tmp")
IGNORED_SUFFIXES = {".log", ".tmp", ".pyc"}

SURFACE_NAMES = {
    "narrative_quality_audit": "Narrative quality audit",
    "portfolio_narrative_workspace": "Portfolio narrative workspace",
    "production_readiness_assistant": "Production readiness assistant",
    "product_shell": "Product shell",
    "route_registry": "Product shell route registry",
    "artifact_index": "Artifact index",
}


def build_artifact_index(*, output_root: Path, project_root: Path) -> dict[str, Any]:
    output_root = output_root.resolve()
    project_root = project_root.resolve()
    artifacts = _artifact_rows(output_root=output_root, project_root=project_root)
    _mark_superseded(artifacts)
    return {
        "version": "product-shell-artifact-index-v1",
        "generated_at": _utc_now(),
        "output_root": _safe_relative_path(output_root, project_root),
        "summary": {
            "artifact_count": len(artifacts),
            "html_link_count": sum(1 for artifact in artifacts if artifact.get("html_path")),
            "json_link_count": sum(1 for artifact in artifacts if artifact.get("json_path")),
            "warning_count": sum(_int(artifact.get("warning_count")) for artifact in artifacts),
            "stale_or_superseded_count": sum(1 for artifact in artifacts if artifact.get("superseded")),
        },
        "artifacts": artifacts,
        "redaction_policy": {
            "excluded_path_categories": [
                "credential_like_paths",
                "temporary_or_log_outputs",
            ],
        },
    }


def render_artifact_index_html(index: dict[str, Any]) -> str:
    summary = _mapping(index.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>产物索引预览</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>产物索引预览</h1>",
            '<section class="summary">',
            _html_kv("产物数", summary.get("artifact_count", 0)),
            _html_kv("HTML 链接", summary.get("html_link_count", 0)),
            _html_kv("JSON 链接", summary.get("json_link_count", 0)),
            _html_kv("告警数", summary.get("warning_count", 0)),
            "</section>",
            _artifact_table(_list(index.get("artifacts"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _artifact_rows(*, output_root: Path, project_root: Path) -> list[dict[str, Any]]:
    rows = []
    for json_path in sorted(output_root.rglob("*.json")):
        if _is_sensitive_path(json_path):
            continue
        html_path = json_path.with_suffix(".html")
        payload = _read_json_object(json_path)
        if payload is None:
            continue
        stem = json_path.stem
        surface = _surface_name(stem)
        generated_at = str(payload.get("generated_at") or _mtime_iso(json_path))
        warning_count = _warning_count(payload)
        artifact = {
            "artifact_id": _artifact_id(json_path, output_root),
            "artifact_type": stem,
            "surface": surface,
            "run_id": _run_id(json_path, output_root),
            "generated_at": generated_at,
            "json_path": _safe_relative_path(json_path, project_root),
            "html_path": _safe_relative_path(html_path, project_root) if html_path.exists() else "",
            "status": str(payload.get("status") or "unknown"),
            "warning_count": warning_count,
            "source_mode": _source_mode(payload),
            "freshness_status": _freshness_status(payload),
            "superseded": False,
        }
        rows.append(artifact)
    return sorted(rows, key=lambda item: (str(item.get("generated_at")), str(item.get("artifact_id"))))


def _mark_superseded(artifacts: list[dict[str, Any]]) -> None:
    latest_by_type: dict[str, str] = {}
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type") or "")
        generated_at = str(artifact.get("generated_at") or "")
        if generated_at >= latest_by_type.get(artifact_type, ""):
            latest_by_type[artifact_type] = generated_at
    for artifact in artifacts:
        artifact["superseded"] = str(artifact.get("generated_at") or "") < latest_by_type.get(
            str(artifact.get("artifact_type") or ""),
            "",
        )


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _artifact_id(path: Path, output_root: Path) -> str:
    relative = path.relative_to(output_root).as_posix()
    digest = sha256(relative.encode("utf-8")).hexdigest()[:10]
    return f"ART_{digest}"


def _run_id(path: Path, output_root: Path) -> str:
    relative = path.relative_to(output_root)
    if len(relative.parts) >= 2:
        return relative.parts[-2]
    return "root"


def _surface_name(stem: str) -> str:
    return SURFACE_NAMES.get(stem, stem.replace("_", " ").title())


def _warning_count(payload: dict[str, Any]) -> int:
    if "warning_count" in payload:
        return _int(payload.get("warning_count"))
    summary = _mapping(payload.get("summary"))
    if "warning_count" in summary:
        return _int(summary.get("warning_count"))
    warnings = payload.get("warnings")
    return len(warnings) if isinstance(warnings, list) else 0


def _source_mode(payload: dict[str, Any]) -> str:
    if payload.get("source_mode"):
        return str(payload["source_mode"])
    source = _mapping(payload.get("narrative_source"))
    if source.get("source"):
        return str(source["source"])
    return str(payload.get("source") or "generated_artifact")


def _freshness_status(payload: dict[str, Any]) -> str:
    if payload.get("freshness_status"):
        return str(payload["freshness_status"])
    freshness = _mapping(payload.get("freshness"))
    if freshness.get("freshness_status"):
        return str(freshness["freshness_status"])
    return str(payload.get("status") or "unknown")


def _safe_relative_path(path: Path, project_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(project_root)
    except ValueError:
        return ""
    if any(part == ".." for part in relative.parts):
        return ""
    return relative.as_posix()


def _is_sensitive_path(path: Path) -> bool:
    lower = path.as_posix().lower()
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True
    return any(part in lower for part in SENSITIVE_PATH_PARTS)


def _artifact_table(artifacts: list[Any]) -> str:
    rows = [_mapping(artifact) for artifact in artifacts]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in (
            "Surface",
            "Run",
            "Status",
            "Freshness",
            "Warnings",
            "HTML 路径",
            "JSON 路径",
            "Superseded",
        )
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('surface'))}</td>"
        f"<td>{_html_text(row.get('run_id'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('freshness_status'))}</td>"
        f"<td>{_html_text(row.get('warning_count'))}</td>"
        f"<td>{_html_text(row.get('html_path'))}</td>"
        f"<td>{_html_text(row.get('json_path'))}</td>"
        f"<td>{_html_text(row.get('superseded'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>产物列表</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f7f8fa; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
