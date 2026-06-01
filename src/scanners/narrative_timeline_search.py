from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from typing import Any


def build_narrative_timeline_search(
    *,
    source_events: list[dict[str, Any]],
    query: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    normalized_query = _normalize_query(query or {})
    normalized_events = [_normalize_event(event) for event in source_events]
    matched = [event for event in normalized_events if _matches(event, normalized_query)]
    page = normalized_query["page"]
    page_size = normalized_query["page_size"]
    start = (page - 1) * page_size
    results = matched[start : start + page_size]
    degraded_sources = [
        {
            "source_event_id": event["source_event_id"],
            "source_id": event["source_id"],
            "degradation_status": event["degradation_status"],
            "degradation_reason": event["degradation_reason"],
        }
        for event in normalized_events
        if event["degradation_status"] not in {"", "ok"}
    ]
    return {
        "version": "narrative-timeline-search-v1",
        "generated_at": generated_at or _utc_now(),
        "query": normalized_query,
        "summary": {
            "raw_event_count": len(source_events),
            "matched_event_count": len(matched),
            "returned_event_count": len(results),
            "degraded_source_count": len(degraded_sources),
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": len(matched),
            "has_next_page": start + page_size < len(matched),
        },
        "contract": {
            "provider_access_allowed": False,
            "response_schema": "timeline_search_results",
            "filters": [
                "narrative",
                "ticker",
                "sector",
                "concept",
                "source_type",
                "freshness",
                "quality_state",
            ],
            "citation_required": True,
        },
        "degraded_sources": degraded_sources,
        "results": results,
    }


def render_narrative_timeline_search_html(payload: dict[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>叙事时间线与来源事件搜索</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>叙事时间线与来源事件搜索</h1>",
            '<section class="summary">',
            _html_kv("匹配事件", summary.get("matched_event_count", 0)),
            _html_kv("返回事件", summary.get("returned_event_count", 0)),
            _html_kv("降级来源", summary.get("degraded_source_count", 0)),
            "<p>本页面索引已有 source-event artifact，不直接访问 Provider。</p>",
            "</section>",
            _results_table(_list(payload.get("results"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _normalize_query(query: dict[str, Any]) -> dict[str, Any]:
    page = _positive_int(query.get("page"), default=1)
    page_size = min(_positive_int(query.get("page_size"), default=50), 200)
    return {
        "narrative": str(query.get("narrative") or ""),
        "ticker": str(query.get("ticker") or ""),
        "sector": str(query.get("sector") or ""),
        "concept": str(query.get("concept") or ""),
        "source_type": str(query.get("source_type") or ""),
        "freshness": str(query.get("freshness") or ""),
        "quality_state": str(query.get("quality_state") or ""),
        "page": page,
        "page_size": page_size,
    }


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    source_event_id = str(event.get("source_event_id") or event.get("id") or _stable_event_id(event))
    published_at = str(event.get("published_at") or event.get("event_time") or "")
    source_id = str(event.get("provider") or event.get("source_id") or event.get("source") or "")
    url = str(event.get("url") or event.get("evidence_url") or "")
    quality_state = str(event.get("quality_state") or event.get("trust_tier") or event.get("trust_state") or "")
    return {
        "source_event_id": source_event_id,
        "timeline_bucket": published_at[:10],
        "published_at": published_at,
        "title": str(event.get("title") or event.get("headline") or ""),
        "source_id": source_id,
        "source_type": str(event.get("source_kind") or event.get("source_type") or ""),
        "quality_state": quality_state,
        "freshness": _freshness(published_at),
        "entities": {
            "tickers": _strings(event.get("stock_codes") or event.get("tickers")),
            "sectors": _strings(event.get("sectors")),
            "concepts": _strings(event.get("concepts") or event.get("narrative_hints")),
            "narratives": _strings(event.get("narrative_hints") or event.get("topics")),
        },
        "citations": {
            "source_id": source_id,
            "source_event_id": source_event_id,
            "evidence_id": str(event.get("evidence_id") or source_event_id),
            "evidence_url": url,
        },
        "filters_matched": {
            "quality_state": quality_state,
        },
        "degradation_status": str(event.get("degradation_status") or ""),
        "degradation_reason": str(event.get("degradation_reason") or event.get("warning") or ""),
    }


def _matches(event: dict[str, Any], query: dict[str, Any]) -> bool:
    entities = _mapping(event.get("entities"))
    checks = [
        _contains(_list(entities.get("narratives")), query["narrative"]),
        _contains(_list(entities.get("tickers")), query["ticker"]),
        _contains(_list(entities.get("sectors")), query["sector"]),
        _contains(_list(entities.get("concepts")), query["concept"]),
        _equals(event.get("source_type"), query["source_type"]),
        _equals(event.get("freshness"), query["freshness"]),
        _equals(event.get("quality_state"), query["quality_state"]),
    ]
    return all(checks)


def _contains(values: list[Any], needle: str) -> bool:
    if not needle:
        return True
    normalized = needle.casefold()
    return any(normalized in str(value).casefold() for value in values)


def _equals(value: Any, expected: str) -> bool:
    if not expected:
        return True
    return str(value or "").casefold() == expected.casefold()


def _freshness(published_at: str) -> str:
    if published_at.startswith("2026-06-02"):
        return "today"
    if published_at:
        return "historical"
    return "unknown"


def _results_table(results: list[Any]) -> str:
    rows = [_mapping(result) for result in results]
    if not rows:
        return "<section><h2>搜索结果</h2><p>没有匹配的来源事件。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("日期", "标题", "来源", "质量", "证据链接")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('timeline_bucket'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(row.get('source_id'))}</td>"
        f"<td>{_html_text(row.get('quality_state'))}</td>"
        f"<td>{_html_text(_mapping(row.get('citations')).get('evidence_url'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>搜索结果</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def _stable_event_id(event: dict[str, Any]) -> str:
    return str(abs(hash(json.dumps(event, ensure_ascii=False, sort_keys=True))))


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
