from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any
from urllib.parse import urlparse

OFFICIAL_SOURCE_KINDS = {"official_filings", "official_disclosures", "official_sources"}
CONTEXT_OR_HEAT_TIERS = {"context_only", "heat_signal_only"}


def build_candidate_evidence_detail(
    *,
    candidate_id: str,
    review_queue: dict[str, Any],
    source_payload: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    candidate = _candidate_row(candidate_id, review_queue)
    source_events = _source_events_by_id(source_payload)
    evidence_rows = [
        _evidence_row(
            link=_mapping(link),
            source_event=source_events.get(str(_mapping(link).get("source_event_id") or "")),
            candidate=candidate,
        )
        for link in _list(candidate.get("evidence_links"))
        if isinstance(link, dict)
    ]
    groups = _groups(evidence_rows)
    support_class = _support_class(candidate)
    return {
        "version": "candidate-evidence-detail-v1",
        "generated_at": generated_at or _utc_now(),
        "candidate": {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "title": str(candidate.get("title") or ""),
            "topic": str(candidate.get("topic") or ""),
            "candidate_state": str(candidate.get("candidate_state") or ""),
            "freshness_state": str(candidate.get("freshness_state") or ""),
            "support_class": support_class,
            "review_priority": str(candidate.get("review_priority") or ""),
        },
        "summary": {
            "source_event_count": len(evidence_rows),
            "visible_event_count": len(evidence_rows),
            "missing_event_count": sum(1 for row in evidence_rows if row["event_status"] == "missing"),
            "degraded_event_count": sum(1 for row in evidence_rows if row["event_status"] == "degraded"),
            "official_event_count": sum(1 for row in evidence_rows if row["source_kind"] in OFFICIAL_SOURCE_KINDS),
            "context_or_heat_event_count": sum(
                1
                for row in evidence_rows
                if row["promotion_evidence_role"] in {
                    "context_only_insufficient",
                    "heat_signal_only_insufficient",
                }
            ),
        },
        "trust_promotion_allowed": False,
        "why_untrusted": _why_untrusted(support_class),
        "promotion_requirements": _promotion_requirements(support_class),
        "events": evidence_rows,
        "groups": groups,
        "disclosure": {
            "llm_fact_extraction_allowed": False,
            "pdf_body_extraction_allowed": False,
            "trusted_promotion_action_allowed": False,
        },
    }


def render_candidate_evidence_detail_html(detail: dict[str, Any]) -> str:
    candidate = _mapping(detail.get("candidate"))
    summary = _mapping(detail.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>候选叙事证据详情</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>候选叙事证据详情</h1>",
            '<section class="summary">',
            _html_kv("候选", candidate.get("title")),
            _html_kv("候选状态", candidate.get("candidate_state")),
            _html_kv("证据数", summary.get("source_event_count", 0)),
            _html_kv("缺失证据", summary.get("missing_event_count", 0)),
            _html_kv("降级证据", summary.get("degraded_event_count", 0)),
            f"<p>{_html_text(detail.get('why_untrusted'))}</p>",
            "<p>候选仍未升级为可信叙事；本页只展示来源事件，不执行可信提升。</p>",
            "</section>",
            _requirements_section(_strings(detail.get("promotion_requirements"))),
            _groups_section(_list(detail.get("groups"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _candidate_row(candidate_id: str, review_queue: dict[str, Any]) -> dict[str, Any]:
    for row in _list(review_queue.get("rows")):
        if isinstance(row, dict) and str(row.get("candidate_id") or "") == candidate_id:
            return row
    raise ValueError(f"candidate_id not found in review queue: {candidate_id}")


def _source_events_by_id(source_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for result in _list(source_payload.get("source_results")):
        result_map = _mapping(result)
        source_kind = str(result_map.get("source_kind") or "")
        result_degradation = _strings(result_map.get("degradation_events"))
        for row in _list(result_map.get("rows")):
            if not isinstance(row, dict):
                continue
            source_event_id = str(row.get("source_event_id") or row.get("event_id") or "")
            if not source_event_id:
                continue
            row_degradation = _strings(row.get("degradation_events"))
            events[source_event_id] = {
                **row,
                "source_kind": str(row.get("source_kind") or source_kind),
                "degradation_events": _unique(row_degradation + result_degradation),
            }
    for row in _list(source_payload.get("source_events")):
        if isinstance(row, dict):
            source_event_id = str(row.get("source_event_id") or row.get("event_id") or "")
            if source_event_id:
                events[source_event_id] = row
    return events


def _evidence_row(
    *,
    link: dict[str, Any],
    source_event: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    source_event_id = str(link.get("source_event_id") or "")
    if source_event is None:
        return {
            "source_event_id": source_event_id,
            "event_status": "missing",
            "source_kind": "missing",
            "trust_tier": "candidate_untrusted",
            "source_url": "",
            "domain": "",
            "title": str(link.get("title") or ""),
            "event_time": str(link.get("event_time") or ""),
            "provider": str(link.get("provider") or ""),
            "source_quality": "missing",
            "retention_status": "missing",
            "extraction_status": "missing",
            "freshness_state": str(candidate.get("freshness_state") or ""),
            "degradation_events": ["SOURCE_EVENT_NOT_FOUND"],
            "promotion_evidence_role": "missing_insufficient",
        }
    degradation_events = _strings(source_event.get("degradation_events"))
    trust_tier = _trust_tier(source_event)
    source_kind = str(source_event.get("source_kind") or "")
    return {
        "source_event_id": source_event_id,
        "event_status": "degraded" if degradation_events else "available",
        "source_kind": source_kind,
        "trust_tier": trust_tier,
        "source_url": str(source_event.get("source_url") or ""),
        "domain": _domain(str(source_event.get("source_url") or "")),
        "title": str(source_event.get("title") or link.get("title") or ""),
        "event_time": str(source_event.get("event_time") or link.get("event_time") or ""),
        "provider": str(source_event.get("provider") or source_event.get("source_provider") or ""),
        "source_quality": _source_quality(source_event),
        "retention_status": str(source_event.get("retention_policy") or ""),
        "extraction_status": _extraction_status(source_event),
        "freshness_state": str(candidate.get("freshness_state") or ""),
        "degradation_events": degradation_events,
        "promotion_evidence_role": _promotion_evidence_role(
            source_kind=source_kind,
            trust_tier=trust_tier,
        ),
    }


def _groups(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in events:
        key = (str(event.get("source_kind") or ""), str(event.get("trust_tier") or ""))
        grouped.setdefault(key, []).append(event)
    return [
        {
            "source_kind": source_kind,
            "trust_tier": trust_tier,
            "event_count": len(rows),
            "events": rows,
        }
        for (source_kind, trust_tier), rows in sorted(
            grouped.items(), key=lambda item: (_source_kind_rank(item[0][0]), item[0][0], item[0][1])
        )
    ]


def _source_kind_rank(source_kind: str) -> int:
    if source_kind in OFFICIAL_SOURCE_KINDS:
        return 0
    if source_kind in {"news_context", "open_news_index", "industry_media"}:
        return 1
    if source_kind == "social_heat":
        return 2
    if source_kind == "missing":
        return 9
    return 5


def _promotion_evidence_role(*, source_kind: str, trust_tier: str) -> str:
    if source_kind in OFFICIAL_SOURCE_KINDS:
        return "official_or_primary_evidence"
    if trust_tier == "heat_signal_only":
        return "heat_signal_only_insufficient"
    if trust_tier in CONTEXT_OR_HEAT_TIERS:
        return "context_only_insufficient"
    return "candidate_evidence"


def _why_untrusted(support_class: str) -> str:
    if support_class == "heat_signal_only":
        return "热度信号不能单独升级为可信叙事，需要官方或主来源证据。"
    if support_class == "context_only":
        return "上下文证据不足以单独升级为可信叙事，需要官方或主来源证据。"
    if support_class == "official_fact_backed":
        return "已有官方或主来源候选证据，但仍需要人工复核动作和 trust preflight。"
    return "候选缺少足够来源质量和复核证据。"


def _promotion_requirements(support_class: str) -> list[str]:
    base = ["需要官方或主来源证据，并保留 source_event_id、URL、时间和来源质量标签。"]
    if support_class in {"context_only", "heat_signal_only"}:
        return base + ["当前上下文或热度证据只能作为线索，不能单独升级。"]
    return base + ["需要 review action ledger 记录人工判断，再运行 trust preflight。"]


def _requirements_section(requirements: list[str]) -> str:
    items = "".join(f"<li>{_html_text(item)}</li>" for item in requirements)
    return f"<section><h2>升级前要求</h2><ul>{items}</ul></section>"


def _groups_section(groups: list[Any]) -> str:
    sections = []
    for group in groups:
        row = _mapping(group)
        title = f"{row.get('source_kind')} / {row.get('trust_tier')}"
        sections.append(
            "<section>"
            f"<h2>{_html_text(title)}</h2>"
            f"{_events_table(_list(row.get('events')))}"
            "</section>"
        )
    return "".join(sections)


def _events_table(events: list[Any]) -> str:
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in (
            "source_event_id",
            "状态",
            "标题",
            "URL",
            "来源",
            "质量",
            "留存/抽取",
            "新鲜度",
            "降级",
            "升级作用",
        )
    )
    body = "".join(_event_html(_mapping(event)) for event in events)
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _event_html(event: dict[str, Any]) -> str:
    role_text = _role_label(str(event.get("promotion_evidence_role") or ""))
    source_url = str(event.get("source_url") or "")
    link = (
        f'<a href="{_html_text(source_url)}">{_html_text(source_url)}</a>'
        if source_url
        else ""
    )
    return (
        "<tr>"
        f"<td>{_html_text(event.get('source_event_id'))}</td>"
        f"<td>{_html_text(event.get('event_status'))}</td>"
        f"<td>{_html_text(event.get('title'))}</td>"
        f"<td>{link}</td>"
        f"<td>{_html_text(event.get('provider'))}<br>{_html_text(event.get('domain'))}</td>"
        f"<td>{_html_text(event.get('source_quality'))}</td>"
        f"<td>{_html_text(event.get('retention_status'))}<br>{_html_text(event.get('extraction_status'))}</td>"
        f"<td>{_html_text(event.get('freshness_state'))}</td>"
        f"<td>{_html_text(', '.join(_strings(event.get('degradation_events'))))}</td>"
        f"<td>{_html_text(role_text)}</td>"
        "</tr>"
    )


def _role_label(value: str) -> str:
    mapping = {
        "official_or_primary_evidence": "官方或主来源证据",
        "context_only_insufficient": "上下文证据不足以单独升级",
        "heat_signal_only_insufficient": "热度信号不足以单独升级",
        "missing_insufficient": "缺失证据不足以升级",
        "candidate_evidence": "候选证据",
    }
    return mapping.get(value, value)


def _support_class(candidate: dict[str, Any]) -> str:
    return str(_mapping(candidate.get("trust_tier_summary")).get("support_class") or "")


def _trust_tier(source_event: dict[str, Any]) -> str:
    return str(
        source_event.get("trust_tier")
        or source_event.get("source_trust_tier")
        or _mapping(source_event.get("meta")).get("trust_tier")
        or "candidate_untrusted"
    )


def _source_quality(source_event: dict[str, Any]) -> str:
    value = source_event.get("source_quality")
    if isinstance(value, dict):
        return str(value.get("label") or "")
    return str(value or "")


def _extraction_status(source_event: dict[str, Any]) -> str:
    provider_metadata = _mapping(source_event.get("provider_metadata"))
    extraction = _mapping(source_event.get("extraction"))
    if extraction.get("status"):
        return str(extraction["status"])
    if provider_metadata.get("extraction_status"):
        return str(provider_metadata["extraction_status"])
    if source_event.get("metadata_only") is True:
        return "metadata_only"
    return "available"


def _domain(source_url: str) -> str:
    if not source_url:
        return ""
    return urlparse(source_url).netloc


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
a { color: #1d4ed8; overflow-wrap: anywhere; }
"""


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
