from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Protocol

WORKSPACE_STATE_VERSION = "product-shell-workspace-state-v1"
ALLOWED_SURFACES = {
    "narrative_radar",
    "narrative_quality",
    "portfolio_workspace",
    "production_readiness",
    "artifact_browser",
    "source_quality",
    "fresh_narrative_digest",
}
SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|token|secret|password|credential|private[_-]?key)",
    re.IGNORECASE,
)


class WorkspaceRepository(Protocol):
    def load(self) -> dict[str, Any]:
        ...

    def save(self, state: dict[str, Any]) -> dict[str, Any]:
        ...


class JsonWorkspaceRepository:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return build_default_workspace_state()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        validate_workspace_state(payload)
        return payload

    def save(self, state: dict[str, Any]) -> dict[str, Any]:
        validate_workspace_state(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return state

    def upsert_saved_view(
        self,
        view: dict[str, Any],
        *,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        state = save_workspace_view(self.load(), view, updated_at=updated_at)
        return self.save(state)


def build_default_workspace_state(
    *,
    generated_at: str | None = None,
    workspace_id: str = "local-default",
) -> dict[str, Any]:
    now = generated_at or _utc_now()
    state = {
        "version": WORKSPACE_STATE_VERSION,
        "workspace_id": workspace_id,
        "generated_at": now,
        "updated_at": now,
        "storage_backend": "json_file",
        "summary": {
            "saved_view_count": 0,
            "artifact_index_count": 0,
        },
        "shell_state": {
            "selected_route": "/",
            "default_mode": "demo",
        },
        "saved_views": [],
        "artifact_indexes": [],
        "validation_policy": {
            "sensitive_values_allowed": False,
            "trusted_market_data_allowed": False,
        },
        "migration_contract": {
            "repository_interface": "WorkspaceRepository",
            "schema_version": "workspace-state-schema-v1",
            "supported_backends": ["json_file", "sqlite", "postgres"],
            "authoritative_records_mutated": False,
        },
    }
    validate_workspace_state(state)
    return state


def save_workspace_view(
    state: dict[str, Any],
    view: dict[str, Any],
    *,
    updated_at: str | None = None,
) -> dict[str, Any]:
    validate_workspace_state(state)
    normalized_view = _normalize_view(view, updated_at=updated_at)
    next_state = deepcopy(state)
    saved_views = [
        existing
        for existing in _list(next_state.get("saved_views"))
        if _mapping(existing).get("view_id") != normalized_view["view_id"]
    ]
    saved_views.append(normalized_view)
    next_state["saved_views"] = sorted(saved_views, key=lambda item: str(item.get("view_id") or ""))
    next_state["updated_at"] = updated_at or _utc_now()
    next_state["summary"] = _summary(next_state)
    validate_workspace_state(next_state)
    return next_state


def validate_workspace_state(state: dict[str, Any]) -> None:
    if not isinstance(state, dict):
        raise ValueError("workspace state must be a mapping")
    if state.get("version") != WORKSPACE_STATE_VERSION:
        raise ValueError("workspace state version is unsupported")
    if _contains_secret_key(state):
        raise ValueError("workspace state must not persist secret-like keys")
    for view in _list(state.get("saved_views")):
        _normalize_view(_mapping(view), updated_at=_mapping(view).get("updated_at"))


def render_workspace_state_html(state: dict[str, Any]) -> str:
    validate_workspace_state(state)
    summary = _mapping(state.get("summary"))
    saved_views = [_mapping(view) for view in _list(state.get("saved_views"))]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>本地工作区状态</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>本地工作区状态</h1>",
            '<section class="summary">',
            _html_kv("保存视图", summary.get("saved_view_count", 0)),
            _html_kv("存储后端", state.get("storage_backend")),
            _html_kv("更新时间", state.get("updated_at")),
            "<p>本地工作区状态只保存页面选择、过滤器、排序和非敏感索引；不保存密钥。</p>",
            "<p>该状态不会修改可信市场数据或 Narrative Service 记录。</p>",
            "</section>",
            _saved_views_table(saved_views),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _normalize_view(view: dict[str, Any], *, updated_at: str | None = None) -> dict[str, Any]:
    if not isinstance(view.get("view_id"), str) or not view["view_id"].strip():
        raise ValueError("saved view view_id must be a non-empty string")
    if not isinstance(view.get("label"), str) or not view["label"].strip():
        raise ValueError("saved view label must be a non-empty string")
    surface = str(view.get("surface") or "")
    if surface not in ALLOWED_SURFACES:
        raise ValueError(f"unsupported surface: {surface}")
    if _contains_secret_key(view):
        raise ValueError("saved view must not persist secret-like keys")
    now = updated_at or _utc_now()
    return {
        "view_id": view["view_id"].strip(),
        "label": view["label"].strip(),
        "surface": surface,
        "selected_route": str(view.get("selected_route") or ""),
        "filters": _sorted_mapping(_mapping(view.get("filters"))),
        "sorting": _sorted_mapping(_mapping(view.get("sorting"))),
        "created_at": str(view.get("created_at") or now),
        "updated_at": now,
    }


def _summary(state: dict[str, Any]) -> dict[str, int]:
    return {
        "saved_view_count": len(_list(state.get("saved_views"))),
        "artifact_index_count": len(_list(state.get("artifact_indexes"))),
    }


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if SECRET_KEY_PATTERN.search(str(key)):
                return True
            if _contains_secret_key(nested):
                return True
    if isinstance(value, list):
        return any(_contains_secret_key(item) for item in value)
    return False


def _saved_views_table(saved_views: list[dict[str, Any]]) -> str:
    if not saved_views:
        return "<section><h2>保存视图</h2><p>还没有保存视图。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("视图", "页面", "路由", "过滤器", "排序", "更新时间")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(view.get('label'))}</td>"
        f"<td>{_html_text(view.get('surface'))}</td>"
        f"<td>{_html_text(view.get('selected_route'))}</td>"
        f"<td>{_html_text(json.dumps(view.get('filters'), ensure_ascii=False, sort_keys=True))}</td>"
        f"<td>{_html_text(json.dumps(view.get('sorting'), ensure_ascii=False, sort_keys=True))}</td>"
        f"<td>{_html_text(view.get('updated_at'))}</td>"
        "</tr>"
        for view in saved_views
    )
    return f"<section><h2>保存视图</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _sorted_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in sorted(value)}


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
