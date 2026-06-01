from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_product_shell_route_registry(
    *,
    artifact_index_path: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    routes = [
        _route(
            route_id="home",
            path="/",
            label_zh="产品首页",
            label_en="Product home",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="route_registry + artifact_index",
            html_path="index.html",
            freshness_status="generated",
        ),
        _route(
            route_id="narrative_radar",
            path="/narratives/radar",
            label_zh="叙事雷达",
            label_en="Narrative Radar",
            owner_service="Narrative Service",
            data_source_type="live_api",
            source="/api/v1/narratives/radar",
            freshness_status="service_reported",
        ),
        _route(
            route_id="narrative_data",
            path="/narratives/data",
            label_zh="真实叙事数据",
            label_en="Real narrative data",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="Narrative Service artifacts + FNI reviewed registry",
            json_path="outputs/product_shell/round8-current/narrative_data.json",
            html_path="outputs/product_shell/round8-current/narrative_data.html",
            freshness_status="generated",
        ),
        _route(
            route_id="narrative_quality",
            path="/narratives/quality",
            label_zh="叙事质量审计",
            label_en="Narrative quality audit",
            owner_service="Narrative Service",
            data_source_type="live_api",
            source="/api/v1/narratives/quality/audit",
            freshness_status="service_reported",
        ),
        _route(
            route_id="fresh_narrative_digest",
            path="/narratives/digest",
            label_zh="今日叙事监控摘要",
            label_en="Fresh narrative digest",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="outputs/fresh_narrative_digest/current/",
            json_path="outputs/fresh_narrative_digest/current/fresh_narrative_digest.json",
            html_path="outputs/fresh_narrative_digest/current/fresh_narrative_digest.html",
            freshness_status="artifact_reported",
        ),
        _route(
            route_id="portfolio_workspace",
            path="/workspace/portfolio",
            label_zh="组合叙事工作台",
            label_en="Portfolio narrative workspace",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="outputs/portfolio_narrative_workspace/",
            json_path="outputs/portfolio_narrative_workspace/round6-final/portfolio_narrative_workspace.json",
            html_path="outputs/portfolio_narrative_workspace/round6-final/portfolio_narrative_workspace.html",
            freshness_status="artifact_reported",
        ),
        _route(
            route_id="workspace_state",
            path="/workspace/saved-views",
            label_zh="本地工作区状态",
            label_en="Local workspace state",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="outputs/product_shell/round8-current/workspace_state.json",
            json_path="outputs/product_shell/round8-current/workspace_state.json",
            html_path="outputs/product_shell/round8-current/workspace_state.html",
            freshness_status="generated",
        ),
        _route(
            route_id="production_readiness",
            path="/ops/production-readiness",
            label_zh="生产就绪助手",
            label_en="Production readiness assistant",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="outputs/production_readiness_assistant/",
            json_path="outputs/production_readiness_assistant/round7-final/production_readiness_assistant.json",
            html_path="outputs/production_readiness_assistant/round7-final/production_readiness_assistant.html",
            freshness_status="artifact_reported",
        ),
        _route(
            route_id="source_quality",
            path="/sources/quality",
            label_zh="来源质量仪表盘",
            label_en="Source quality dashboard",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="source governance + reliability + schema + gateway probe artifacts",
            json_path="outputs/product_shell/round8-current/source_quality_dashboard.json",
            html_path="outputs/product_shell/round8-current/source_quality_dashboard.html",
            freshness_status="generated",
        ),
        _route(
            route_id="artifacts",
            path="/artifacts",
            label_zh="产物浏览器",
            label_en="Generated artifacts",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source=artifact_index_path,
            json_path=artifact_index_path,
            html_path="artifact_browser.html",
            freshness_status="generated",
        ),
        _route(
            route_id="config_preflight",
            path="/ops/config-preflight",
            label_zh="配置与预检",
            label_en="Configuration preflight",
            owner_service="FNI",
            data_source_type="generated_artifact",
            source="product shell release preflight",
            json_path="outputs/product_shell/round8-current/config_preflight.json",
            html_path="outputs/product_shell/round8-current/config_preflight.html",
            freshness_status="generated",
        ),
    ]
    return {
        "version": "product-shell-route-registry-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": _summary(routes),
        "routes": routes,
        "global_client_policy": {
            "provider_access_allowed": False,
            "score_recomputation_allowed": False,
            "business_logic_location": "service_or_artifact_only",
        },
    }


def render_route_registry_preview(registry: dict[str, Any]) -> str:
    summary = _mapping(registry.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>产品壳路由注册表</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>产品壳路由注册表</h1>",
            '<section class="summary">',
            _html_kv("路由数", summary.get("route_count", 0)),
            _html_kv("Live API", summary.get("live_api_route_count", 0)),
            _html_kv("Generated artifacts", summary.get("generated_artifact_route_count", 0)),
            "<p>产品壳只负责导航和展示数据来源，不在产品壳内重算评分、雷达热度、质量分或组合指标。</p>",
            "</section>",
            _routes_table(_list(registry.get("routes"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _route(
    *,
    route_id: str,
    path: str,
    label_zh: str,
    label_en: str,
    owner_service: str,
    data_source_type: str,
    source: str,
    freshness_status: str,
    json_path: str = "",
    html_path: str = "",
    degradation_status: str = "ok",
) -> dict[str, Any]:
    return {
        "route_id": route_id,
        "path": path,
        "label_zh": label_zh,
        "label_en": label_en,
        "owner_service": owner_service,
        "data_source": {
            "type": data_source_type,
            "source": source,
            "json_path": json_path,
            "html_path": html_path,
            "freshness_status": freshness_status,
            "degradation_status": degradation_status,
        },
        "client_policy": {
            "score_recomputation_allowed": False,
            "provider_access_allowed": False,
            "forbidden_logic": [
                "provider_access",
                "narrative_scoring",
                "quality_scoring",
                "portfolio_aggregation",
                "trading_recommendation",
            ],
        },
    }


def _summary(routes: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "route_count": len(routes),
        "live_api_route_count": _count_type(routes, "live_api"),
        "generated_artifact_route_count": _count_type(routes, "generated_artifact"),
        "fixture_demo_route_count": _count_type(routes, "fixture_demo"),
        "degraded_route_count": sum(
            1
            for route in routes
            if _mapping(route.get("data_source")).get("degradation_status") not in {"", "ok"}
        ),
    }


def _count_type(routes: list[dict[str, Any]], data_source_type: str) -> int:
    return sum(
        1
        for route in routes
        if _mapping(route.get("data_source")).get("type") == data_source_type
    )


def _routes_table(routes: list[Any]) -> str:
    rows = [_mapping(route) for route in routes]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("路由", "页面", "Owner", "数据来源", "新鲜度", "状态")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('path'))}</td>"
        f"<td>{_html_text(row.get('label_zh'))}</td>"
        f"<td>{_html_text(row.get('owner_service'))}</td>"
        f"<td>{_html_text(_mapping(row.get('data_source')).get('type'))}</td>"
        f"<td>{_html_text(_mapping(row.get('data_source')).get('freshness_status'))}</td>"
        f"<td>{_html_text(_mapping(row.get('data_source')).get('degradation_status'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>页面与数据来源</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1120px; margin: 0 auto; padding: 32px 20px 48px; }
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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
