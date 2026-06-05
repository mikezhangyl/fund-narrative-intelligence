from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.fresh_narrative_digest import EXPECTED_GATEWAY_SOURCE_KINDS

SOURCE_KIND_CATEGORY = {
    "official_filings": "官方披露文件",
    "official_disclosures": "中国公告披露",
    "official_sources": "政策/监管/行业官方来源",
    "news_context": "开放新闻/RSS 上下文",
    "open_news_index": "开放新闻索引",
    "industry_media": "行业媒体",
    "social_heat": "社区热度",
    "paid_provider_later": "付费来源暂缓",
}


def build_narrative_source_coverage_gap_report(
    *,
    gateway_probe: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or _utc_now()
    source_results = {
        str(result.get("source_kind") or ""): _mapping(result)
        for result in _list(gateway_probe.get("source_results"))
        if str(result.get("source_kind") or "")
    }
    gaps = [
        _coverage_row(source_kind, source_results.get(source_kind))
        for source_kind in EXPECTED_GATEWAY_SOURCE_KINDS
    ]
    gaps.append(_paid_provider_later_row())
    summary = {
        "expected_source_kind_count": len(EXPECTED_GATEWAY_SOURCE_KINDS),
        "working_count": sum(1 for gap in gaps if gap["coverage_status"] == "working"),
        "missing_count": sum(1 for gap in gaps if gap["coverage_status"] == "missing"),
        "degraded_count": sum(1 for gap in gaps if gap["coverage_status"] == "degraded"),
        "unsupported_count": sum(1 for gap in gaps if gap["coverage_status"] == "unsupported"),
        "auto_created_issue_count": 0,
    }
    return {
        "version": "narrative-source-coverage-gap-report-v1",
        "generated_at": generated,
        "status": "degraded"
        if summary["missing_count"] or summary["degraded_count"]
        else "ok",
        "gateway_probe_generated_at": str(gateway_probe.get("generated_at") or ""),
        "summary": summary,
        "policy": {
            "provider_implementation_allowed": False,
            "web_crawling_allowed": False,
            "paid_provider_selection_allowed": False,
            "auto_create_linear_issues": False,
        },
        "gaps": gaps,
    }


def render_narrative_source_coverage_gap_html(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>Gateway 来源覆盖缺口报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>Gateway 来源覆盖缺口报告</h1>",
            '<section class="summary">',
            _html_kv("状态", report.get("status")),
            _html_kv("可工作来源", summary.get("working_count", 0)),
            _html_kv("缺失来源", summary.get("missing_count", 0)),
            _html_kv("降级来源", summary.get("degraded_count", 0)),
            _html_kv("暂缓来源", summary.get("unsupported_count", 0)),
            "<p>本报告只给出下一步 owner 和原因，不会自动创建 Linear issue。</p>",
            "</section>",
            _gap_table(_list(report.get("gaps"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _coverage_row(source_kind: str, result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return _row(
            source_kind=source_kind,
            coverage_status="missing",
            row_count=0,
            degradation_events=["GATEWAY_SOURCE_KIND_MISSING"],
            owner="Gateway",
            reason="Gateway probe did not include this source kind.",
        )
    row_count = _row_count(result)
    degradation_events = _strings(result.get("degradation_events"))
    status = str(result.get("status") or "")
    if degradation_events or status == "degraded":
        return _row(
            source_kind=source_kind,
            coverage_status="degraded",
            row_count=row_count,
            degradation_events=degradation_events,
            owner="Gateway",
            reason="Gateway returned structured degradation; keep source unstable until repeated evidence improves.",
        )
    if status in {"failed", "blocked"}:
        return _row(
            source_kind=source_kind,
            coverage_status="degraded",
            row_count=row_count,
            degradation_events=degradation_events or [status.upper()],
            owner="Gateway",
            reason="Gateway source kind failed or is blocked.",
        )
    if row_count <= 0:
        return _row(
            source_kind=source_kind,
            coverage_status="missing",
            row_count=0,
            degradation_events=["NO_SOURCE_EVENTS"],
            owner="Gateway",
            reason="Gateway probe returned no usable source-event rows.",
        )
    return _row(
        source_kind=source_kind,
        coverage_status="working",
        row_count=row_count,
        degradation_events=[],
        owner="FNI",
        reason="Gateway source kind has probe evidence; FNI can consume it as unstable/gateway-ready input.",
    )


def _paid_provider_later_row() -> dict[str, Any]:
    return _row(
        source_kind="paid_provider_later",
        coverage_status="unsupported",
        row_count=0,
        degradation_events=[],
        owner="Later",
        reason="Paid providers are explicitly outside current M20 open-source-first scope.",
    )


def _row(
    *,
    source_kind: str,
    coverage_status: str,
    row_count: int,
    degradation_events: list[str],
    owner: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "category": SOURCE_KIND_CATEGORY.get(source_kind, source_kind),
        "coverage_status": coverage_status,
        "row_count": row_count,
        "degradation_events": degradation_events,
        "owner": owner,
        "reason": reason,
        "suggested_next_issue": _suggested_issue(source_kind, coverage_status, owner),
        "auto_create_issue": False,
    }


def _suggested_issue(source_kind: str, coverage_status: str, owner: str) -> dict[str, str]:
    if coverage_status == "working":
        return {
            "owner": owner,
            "reason": "Use probe evidence in FNI artifacts; do not create backlog.",
            "title": "",
        }
    if coverage_status == "unsupported":
        return {
            "owner": owner,
            "reason": "Keep paid-provider evaluation in Later/backlog.",
            "title": "",
        }
    return {
        "owner": owner,
        "reason": "Needs Gateway-side source stability or coverage follow-up.",
        "title": f"[GATEWAY][M20] Improve {source_kind} source-event coverage",
    }


def _row_count(result: dict[str, Any]) -> int:
    explicit = result.get("row_count")
    if isinstance(explicit, int):
        return explicit
    if isinstance(explicit, str) and explicit.isdigit():
        return int(explicit)
    return len(_list(result.get("rows")))


def _gap_table(gaps: list[Any]) -> str:
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("来源", "类别", "状态", "行数", "Owner", "原因", "降级事件", "建议")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('source_kind'))}</td>"
        f"<td>{_html_text(row.get('category'))}</td>"
        f"<td>{_html_text(row.get('coverage_status'))}</td>"
        f"<td>{_html_text(row.get('row_count'))}</td>"
        f"<td>{_html_text(row.get('owner'))}</td>"
        f"<td>{_html_text(row.get('reason'))}</td>"
        f"<td>{_html_text(', '.join(_strings(row.get('degradation_events'))))}</td>"
        f"<td>{_html_text(_mapping(row.get('suggested_next_issue')).get('title'))}</td>"
        "</tr>"
        for row in (_mapping(gap) for gap in gaps)
    )
    return f"<section><h2>覆盖缺口</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


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
