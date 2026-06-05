from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

REVIEW_SOURCE = "docs/product/pm-architect-stage-review-round4-round13-2026-06-02.html"
VALUE_DISPLAY = {
    "ok": "正常",
    "degraded": "已降级",
    "blocked": "已阻塞",
    "missing": "缺失",
    "available": "可用",
    "stale": "过期",
    "official_filings": "官方披露文件",
    "official_disclosures": "官方公告披露",
    "generated_artifacts": "生成产物",
    "social_heat": "社交热度",
    "news_context": "新闻上下文",
    "official_disclosure": "官方披露",
    "public_web_crawler": "公网爬虫",
    "community_page_crawler": "社区页面爬虫",
    "trusted_fact": "可信事实",
    "Trusted Fact": "可信事实",
    "candidate_untrusted": "未验证候选",
    "unknown": "未知",
    "none": "无",
    "metadata_and_public_document_reference": "元数据与公开文档引用",
    "metadata_and_permitted_excerpt": "元数据与允许展示的摘要",
    "metadata_only_until_reviewed": "复核前仅元数据",
    "do_not_store": "不留存",
    "low": "低",
    "medium": "中",
    "high": "高",
    "robots_tos_review_required": "需要 robots/服务条款评审",
    "request_pacing_policy_required": "需要请求节奏策略",
    "missing_required_registry_field": "缺少注册表必填字段",
    "prohibited_behavior_declared": "声明了禁止行为",
    "SEC EDGAR filings": "SEC EDGAR 披露文件",
    "Public industry media candidate": "公网行业媒体候选",
    "Forbidden social scrape": "禁止的社交来源爬取",
    "governance": "来源治理",
    "reliability": "来源可靠性",
    "schema_v2": "来源结构 v2",
    "gateway_probe": "网关探测",
    "Gateway owns acquisition; FNI displays generated contracts, probes, and reports.": (
        "采集由 stock-data-gateway 负责；FNI 只展示生成后的契约、探测和报告。"
    ),
}
ARTIFACT_SPECS = (
    (
        "governance",
        "source_governance/**/source_governance_report.json",
        "source_governance_report.html",
    ),
    (
        "reliability",
        "source_reliability/**/source_reliability_report.json",
        "source_reliability_report.html",
    ),
    (
        "schema_v2",
        "source_schema_v2/**/source_schema_v2_report.json",
        "source_schema_v2_report.html",
    ),
    (
        "gateway_probe",
        "narrative_source_gateway_probe/**/narrative_source_gateway_probe.json",
        "narrative_source_gateway_probe.html",
    ),
)


def build_source_quality_dashboard(
    *,
    project_root: Path,
    output_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    output_root = output_root.resolve()
    generated = generated_at or _utc_now()
    artifacts = [
        _artifact_status(
            artifact_id=artifact_id,
            pattern=pattern,
            html_name=html_name,
            output_root=output_root,
            project_root=project_root,
            generated_at=generated,
        )
        for artifact_id, pattern, html_name in ARTIFACT_SPECS
    ]
    payloads = {
        artifact["artifact_id"]: _read_json_object(Path(str(artifact.get("absolute_json_path"))))
        for artifact in artifacts
        if artifact.get("absolute_json_path")
    }
    sources = _source_rows(
        governance=payloads.get("governance") or {},
        reliability=payloads.get("reliability") or {},
        gateway_probe=payloads.get("gateway_probe") or {},
        artifacts=artifacts,
    )
    missing_artifacts = sum(1 for artifact in artifacts if artifact["status"] == "missing")
    stale_artifacts = sum(1 for artifact in artifacts if artifact["status"] == "stale")
    degraded_sources = sum(1 for source in sources if source["status"] != "ok")
    return {
        "version": "product-shell-source-quality-dashboard-v1",
        "generated_at": generated,
        "status": "degraded" if missing_artifacts or stale_artifacts or degraded_sources else "ok",
        "summary": {
            "source_count": len(sources),
            "trusted_fact_count": sum(1 for source in sources if source["trust_tier"] == "trusted_fact"),
            "degraded_source_count": degraded_sources,
            "missing_artifact_count": missing_artifacts,
            "stale_artifact_count": stale_artifacts,
        },
        "consumer_policy": {
            "provider_access_allowed": False,
            "reliability_recomputation_allowed": False,
            "owner_boundary": "Gateway owns acquisition; FNI displays generated contracts, probes, and reports.",
        },
        "review_source": REVIEW_SOURCE,
        "artifacts": [_public_artifact(artifact) for artifact in artifacts],
        "sources": sources,
    }


def render_source_quality_dashboard_html(dashboard: dict[str, Any]) -> str:
    summary = _mapping(dashboard.get("summary"))
    policy = _mapping(dashboard.get("consumer_policy"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>来源质量仪表盘</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>来源质量仪表盘</h1>",
            '<section class="summary">',
            _html_kv("状态", dashboard.get("status")),
            _html_kv("来源数", summary.get("source_count", 0)),
            _html_kv("可信事实来源", summary.get("trusted_fact_count", 0)),
            _html_kv("降级来源", summary.get("degraded_source_count", 0)),
            _html_kv("缺失产物", summary.get("missing_artifact_count", 0)),
            f"<p>{_html_text(_display_value(policy.get('owner_boundary')))}</p>",
            "<p>产品壳不重新计算来源可靠性分，也不调用外部供应商。</p>",
            f"<p>复核来源: {_html_text(dashboard.get('review_source'))}</p>",
            "</section>",
            _source_table(_list(dashboard.get("sources"))),
            _artifact_table(_list(dashboard.get("artifacts"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _source_rows(
    *,
    governance: dict[str, Any],
    reliability: dict[str, Any],
    gateway_probe: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reliability_by_id = {
        str(score.get("source_id") or ""): score
        for score in _list(reliability.get("scores"))
        if str(score.get("source_id") or "")
    }
    gateway_by_group = _gateway_degradation_by_group(gateway_probe)
    rows = []
    artifact_paths = _artifact_paths_by_id(artifacts)
    for decision in _list(governance.get("decisions")):
        source_id = str(decision.get("source_id") or "")
        score = _mapping(reliability_by_id.get(source_id))
        source_type = str(score.get("source_class") or decision.get("acquisition_mode") or "")
        degradation_events = _strings(score.get("warnings")) + _strings(decision.get("blocked_reasons"))
        degradation_events.extend(_strings(gateway_by_group.get(_source_group(source_id, source_type))))
        trust_tier = "trusted_fact" if score.get("trusted_fact_allowed") is True else _fallback_trust_tier(score)
        status = "ok"
        if str(decision.get("gate_status") or "") == "blocked" or str(score.get("label") or "") == "Avoid":
            status = "blocked"
        elif degradation_events:
            status = "degraded"
        rows.append(
            {
                "source_id": source_id,
                "display_name": str(decision.get("display_name") or score.get("display_name") or source_id),
                "source_group": _source_group(source_id, source_type),
                "source_type": source_type,
                "owner_service": str(decision.get("owner_service") or ""),
                "trust_tier": trust_tier,
                "source_quality_label": str(score.get("label") or "unknown"),
                "license_scope": str(decision.get("license_scope") or ""),
                "retention_policy": str(decision.get("retention_policy") or ""),
                "anti_bot_risk": str(decision.get("anti_bot_risk") or ""),
                "degradation_events": degradation_events,
                "last_generated_at": _latest_generated_at(artifacts),
                "artifact_paths": artifact_paths,
                "status": status,
            }
        )
    return rows


def _gateway_degradation_by_group(gateway_probe: dict[str, Any]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for result in _list(gateway_probe.get("source_results")):
        source_kind = str(result.get("source_kind") or _mapping(result.get("meta")).get("source") or "")
        group = _gateway_source_group(source_kind)
        events = _strings(result.get("degradation_events"))
        if events:
            groups.setdefault(group, []).extend(events)
    return groups


def _gateway_source_group(source_kind: str) -> str:
    lower = source_kind.lower()
    if "filing" in lower or "edgar" in lower:
        return "official_filings"
    if "social" in lower or "heat" in lower:
        return "social_heat"
    if "news" in lower or "industry_media" in lower:
        return "news_context"
    if "disclosure" in lower or "announcement" in lower or "official_sources" in lower:
        return "official_disclosures"
    return "generated_artifacts"


def _source_group(source_id: str, source_type: str) -> str:
    lower = f"{source_id} {source_type}".lower()
    if "edgar" in lower or "filing" in lower:
        return "official_filings"
    if "cninfo" in lower or "disclosure" in lower or "announcement" in lower:
        return "official_disclosures"
    if "news" in lower:
        return "news_context"
    if "social" in lower or "stocktwits" in lower or "community" in lower:
        return "social_heat"
    return "generated_artifacts"


def _fallback_trust_tier(score: dict[str, Any]) -> str:
    label = str(score.get("label") or "")
    if label == "Heat Signal":
        return "heat_signal_only"
    if label in {"Licensed News", "Research Context"}:
        return "context_only"
    if label == "Avoid":
        return "blocked"
    return "candidate_untrusted"


def _artifact_status(
    *,
    artifact_id: str,
    pattern: str,
    html_name: str,
    output_root: Path,
    project_root: Path,
    generated_at: str,
) -> dict[str, Any]:
    candidates = sorted(output_root.glob(pattern))
    json_path = candidates[-1] if candidates else None
    if json_path is None:
        return {
            "artifact_id": artifact_id,
            "status": "missing",
            "json_path": "",
            "html_path": "",
            "generated_at": "",
            "absolute_json_path": "",
        }
    payload = _read_json_object(json_path)
    artifact_generated_at = str(_mapping(payload).get("generated_at") or _mtime_iso(json_path))
    html_path = json_path.with_name(html_name)
    status = "stale" if _is_stale(artifact_generated_at, generated_at) else "available"
    return {
        "artifact_id": artifact_id,
        "status": status,
        "json_path": _safe_relative_path(json_path, project_root),
        "html_path": _safe_relative_path(html_path, project_root) if html_path.exists() else "",
        "generated_at": artifact_generated_at,
        "absolute_json_path": str(json_path),
    }


def _public_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact["artifact_id"],
        "status": artifact["status"],
        "json_path": artifact["json_path"],
        "html_path": artifact["html_path"],
        "generated_at": artifact["generated_at"],
    }


def _artifact_paths_by_id(artifacts: list[dict[str, Any]]) -> dict[str, str]:
    return {
        f"{artifact['artifact_id']}_json": str(artifact.get("json_path") or "")
        for artifact in artifacts
    } | {
        f"{artifact['artifact_id']}_html": str(artifact.get("html_path") or "")
        for artifact in artifacts
    }


def _latest_generated_at(artifacts: list[dict[str, Any]]) -> str:
    values = [str(artifact.get("generated_at") or "") for artifact in artifacts]
    return max(values) if values else ""


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _is_stale(artifact_generated_at: str, current_generated_at: str) -> bool:
    artifact_time = _parse_datetime(artifact_generated_at)
    current_time = _parse_datetime(current_generated_at)
    if artifact_time is None or current_time is None:
        return False
    return (current_time - artifact_time).days > 14


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).replace(microsecond=0).isoformat()


def _safe_relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return ""


def _source_table(sources: list[Any]) -> str:
    rows = [_mapping(source) for source in sources]
    if not rows:
        return "<section><h2>来源</h2><p>没有可展示来源；请先生成来源治理与可靠性产物。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("来源", "分组", "类型", "负责人", "信任层级", "质量", "授权", "留存", "反爬", "状态", "降级")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(_display_value(row.get('display_name')))}</td>"
        f"<td>{_html_text(_display_value(row.get('source_group')))}</td>"
        f"<td>{_html_text(_display_value(row.get('source_type')))}</td>"
        f"<td>{_html_text(row.get('owner_service'))}</td>"
        f"<td>{_html_text(_display_value(row.get('trust_tier')))}</td>"
        f"<td>{_html_text(_display_value(row.get('source_quality_label')))}</td>"
        f"<td>{_html_text(_display_value(row.get('license_scope')))}</td>"
        f"<td>{_html_text(_display_value(row.get('retention_policy')))}</td>"
        f"<td>{_html_text(_display_value(row.get('anti_bot_risk')))}</td>"
        f"<td>{_html_text(_display_value(row.get('status')))}</td>"
        f"<td>{_html_text(_display_degradation_events(row.get('degradation_events')))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>来源</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _artifact_table(artifacts: list[Any]) -> str:
    rows = [_mapping(artifact) for artifact in artifacts]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("产物", "状态", "JSON", "HTML", "生成时间")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(_display_value(row.get('artifact_id')))}</td>"
        f"<td>{_html_text(_display_value(row.get('status')))}</td>"
        f"<td>{_html_text(row.get('json_path'))}</td>"
        f"<td>{_html_text(row.get('html_path'))}</td>"
        f"<td>{_html_text(row.get('generated_at'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>来源产物</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(_display_value(value))}</p>"


def _display_degradation_events(value: Any) -> str:
    return "；".join(_display_value(event) for event in _strings(value))


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value or "")
    return VALUE_DISPLAY.get(text, text)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1240px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 13px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
