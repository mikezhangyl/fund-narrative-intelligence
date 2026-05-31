from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_product_shell_payload(
    *,
    route_registry: dict[str, Any],
    artifact_index: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    routes = _list(route_registry.get("routes"))
    artifacts = _list(artifact_index.get("artifacts"))
    return {
        "version": "product-shell-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "route_count": len(routes),
            "artifact_count": len(artifacts),
            "live_api_route_count": _int(_mapping(route_registry.get("summary")).get("live_api_route_count")),
            "generated_artifact_route_count": _int(
                _mapping(route_registry.get("summary")).get("generated_artifact_route_count")
            ),
        },
        "route_registry": route_registry,
        "artifact_index": artifact_index,
        "client_policy_notice": "不在页面内重算雷达、质量或组合指标；页面只读取服务 API 或生成产物。",
    }


def render_product_home_html(shell: dict[str, Any]) -> str:
    summary = _mapping(shell.get("summary"))
    routes = _list(_mapping(shell.get("route_registry")).get("routes"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>Fund Narrative Intelligence 产品首页</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>Fund Narrative Intelligence 产品首页</h1>",
            '<section class="summary">',
            _html_kv("路由数", summary.get("route_count", 0)),
            _html_kv("产物数", summary.get("artifact_count", 0)),
            f"<p>{_html_text(shell.get('client_policy_notice'))}</p>",
            "</section>",
            _route_cards(routes),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def render_artifact_browser_html(shell: dict[str, Any]) -> str:
    artifacts = _list(_mapping(shell.get("artifact_index")).get("artifacts"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>产物浏览器</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>产物浏览器</h1>",
            "<p>这里集中列出本地已生成的 JSON/HTML 产物、运行目录、状态、告警和新鲜度。</p>",
            _artifact_table(artifacts),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _route_cards(routes: list[Any]) -> str:
    cards = []
    for route in routes:
        row = _mapping(route)
        data_source = _mapping(row.get("data_source"))
        cards.append(
            '<article class="card">'
            f"<h2>{_html_text(row.get('label_zh'))}</h2>"
            f"<p>{_html_text(row.get('label_en'))}</p>"
            f"<p><strong>Route:</strong> {_html_text(row.get('path'))}</p>"
            f"<p><strong>Owner:</strong> {_html_text(row.get('owner_service'))}</p>"
            f"<p><strong>Data:</strong> {_html_text(data_source.get('type'))} / {_html_text(data_source.get('freshness_status'))}</p>"
            f"<p><strong>Source:</strong> {_html_text(data_source.get('source'))}</p>"
            "</article>"
        )
    return f"<section><h2>导航</h2><div class=\"cards\">{''.join(cards)}</div></section>"


def _artifact_table(artifacts: list[Any]) -> str:
    rows = [_mapping(artifact) for artifact in artifacts]
    if not rows:
        return "<section><h2>产物列表</h2><p>没有找到可展示产物。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("Surface", "Run", "Status", "Freshness", "HTML", "JSON")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('surface'))}</td>"
        f"<td>{_html_text(row.get('run_id'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('freshness_status'))}</td>"
        f"<td>{_html_text(row.get('html_path'))}</td>"
        f"<td>{_html_text(row.get('json_path'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>产物列表</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.card { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 14px; }
.card h2 { margin-top: 0; font-size: 18px; }
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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
