from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from src.scanners.candidate_narrative_intake import (
    build_candidate_narrative_intake_report,
    render_html_report,
)
from src.scanners.source_event_schema import validate_source_event


def build_news_candidate_intake_report(
    *,
    news_payload: dict[str, Any] | list[dict[str, Any]],
    registry_payload: dict[str, Any],
    provider: str = "gateway_news_briefs",
    source_provider: str = "tushare",
    src: str = "sina",
) -> dict[str, Any]:
    events = news_briefs_to_source_events(
        news_payload=news_payload,
        provider=provider,
        source_provider=source_provider,
        src=src,
    )
    report = build_candidate_narrative_intake_report(
        event_payload={"version": "source-events-from-news-briefs-v1", "events": events},
        registry_payload=registry_payload,
    )
    return {
        **report,
        "version": "news-candidate-intake-v1",
        "news_source_contract": {
            "input": "gateway_or_tushare_news_briefs",
            "provider": provider,
            "source_provider": source_provider,
            "src": src,
            "direct_crawling_allowed": False,
        },
        "news_source_trace": _source_trace(report.get("events")),
    }


def news_briefs_to_source_events(
    *,
    news_payload: dict[str, Any] | list[dict[str, Any]],
    provider: str = "gateway_news_briefs",
    source_provider: str = "tushare",
    src: str = "sina",
) -> list[dict[str, Any]]:
    rows = _rows(news_payload)
    return [
        validate_source_event(
            _source_event_from_news_row(
                row,
                provider=provider,
                source_provider=source_provider,
                src=src,
            )
        )
        for row in rows
        if _is_selected_news_row(row)
    ]


def render_news_candidate_intake_html(report: dict[str, Any]) -> str:
    base = render_html_report(report)
    trace_section = _trace_section(report.get("news_source_trace"))
    return base.replace("</main>", f"{trace_section}\n</main>")


def _source_event_from_news_row(
    row: dict[str, Any],
    *,
    provider: str,
    source_provider: str,
    src: str,
) -> dict[str, Any]:
    raw_provider = str(row.get("source") or row.get("provider") or source_provider)
    raw_src = str(row.get("src") or row.get("source_name") or src)
    title = str(row.get("title") or row.get("headline") or "")
    summary = str(row.get("summary") or row.get("content") or row.get("brief") or "")
    event_time = str(
        row.get("event_time")
        or row.get("datetime")
        or row.get("pub_time")
        or row.get("time")
        or ""
    )
    return {
        "event_id": str(row.get("event_id") or row.get("id") or _stable_id("EVT_NEWS", [raw_provider, raw_src, event_time, title])),
        "source_type": "news",
        "provider": provider,
        "source_url": str(row.get("source_url") or row.get("url") or row.get("link") or ""),
        "event_time": _event_time(event_time),
        "title": title,
        "summary": summary,
        "stock_codes": _strings(row.get("stock_codes") or row.get("symbols")),
        "mentioned_stocks": _mentioned_stocks(row),
        "narrative_hints": _strings(row.get("narrative_hints") or row.get("keywords")),
        "evidence_claims": _evidence_claims(row),
        "candidate_narratives": _candidate_narratives(row),
        "source_metadata": {
            "provider": provider,
            "raw_provider": raw_provider,
            "raw_src": raw_src,
            "source_mode": "normalized_gateway" if provider.startswith("gateway_") else "external_contract",
            "source_row_id": str(row.get("id") or ""),
            "selection_reason": str(row.get("selection_reason") or "selected_news_candidate_hint"),
        },
    }


def _source_trace(events: Any) -> list[dict[str, Any]]:
    trace = []
    for event in events if isinstance(events, list) else []:
        metadata = event.get("source_metadata") if isinstance(event, dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        trace.append(
            {
                "event_id": str(event.get("event_id") or ""),
                "title": str(event.get("title") or ""),
                "raw_provider": str(metadata.get("raw_provider") or ""),
                "raw_src": str(metadata.get("raw_src") or ""),
                "source_url": str(event.get("source_url") or ""),
                "candidate_narratives": [
                    {
                        "narrative_id": str(candidate.get("narrative_id") or ""),
                        "name": str(candidate.get("name") or ""),
                    }
                    for candidate in event.get("candidate_narratives", [])
                    if isinstance(candidate, dict)
                ],
                "trust_status": str(event.get("trust_status") or "candidate_untrusted"),
            }
        )
    return trace


def _rows(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    for key in ("rows", "news_briefs", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _is_selected_news_row(row: dict[str, Any]) -> bool:
    candidates = _candidate_narratives(row)
    return bool(candidates)


def _candidate_narratives(row: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("candidate_narratives", "narrative_candidates"):
        value = row.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _mentioned_stocks(row: dict[str, Any]) -> list[dict[str, str]]:
    value = row.get("mentioned_stocks")
    if isinstance(value, list) and value:
        return [
            {
                "stock_code": str(item.get("stock_code") or item.get("symbol") or ""),
                "stock_name": str(item.get("stock_name") or item.get("name") or ""),
            }
            for item in value
            if isinstance(item, dict)
        ]
    return [{"stock_code": stock_code, "stock_name": ""} for stock_code in _strings(row.get("stock_codes") or row.get("symbols"))]


def _evidence_claims(row: dict[str, Any]) -> list[str]:
    explicit = _strings(row.get("evidence_claims"))
    if explicit:
        return explicit
    summary = str(row.get("summary") or row.get("content") or row.get("brief") or "")
    return [summary] if summary else []


def _event_time(value: str) -> str:
    if not value:
        return ""
    if "T" in value:
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.isoformat()


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1("|".join(str(value or "") for value in values).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:16].upper()}"


def _trace_section(value: Any) -> str:
    rows = value if isinstance(value, list) else []
    if not rows:
        return '<section><h2>新闻来源追踪</h2><p class="empty">没有返回可展示数据。</p></section>'
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('event_id'))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(row.get('raw_provider'))}</td>"
        f"<td>{_html_text(row.get('raw_src'))}</td>"
        f"<td>{_html_text(row.get('trust_status'))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        "<section><h2>新闻来源追踪</h2>"
        "<table><thead><tr><th>事件</th><th>标题</th><th>Provider</th><th>Src</th><th>状态</th></tr></thead>"
        f"<tbody>{body}</tbody></table></section>"
    )


def _html_text(value: Any) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
