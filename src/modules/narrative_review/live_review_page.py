from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from html import escape
from typing import Any
from urllib.parse import urlparse


def build_live_narrative_review_page(
    *,
    topic_results: list[dict[str, Any]],
    generated_at: str | None = None,
    base_url: str = "",
    fixture_mode: bool = True,
) -> dict[str, Any]:
    topics = [_topic_payload(result) for result in topic_results]
    return {
        "version": "live-narrative-review-page-v1",
        "generated_at": generated_at or _utc_now(),
        "base_url": base_url,
        "fixture_mode": fixture_mode,
        "summary": {
            "topic_count": len(topics),
            "candidate_count": sum(1 for topic in topics if topic.get("candidate")),
            "source_event_count": sum(len(_list(topic.get("evidence_events"))) for topic in topics),
            "missing_source_kind_count": sum(
                1
                for topic in topics
                for state in _mapping(topic.get("source_kind_states")).values()
                if _mapping(state).get("status") == "missing"
            ),
            "degraded_source_kind_count": sum(
                1
                for topic in topics
                for state in _mapping(topic.get("source_kind_states")).values()
                if _mapping(state).get("status") == "degraded"
            ),
        },
        "contract": {
            "gateway_only_source_access": True,
            "trusted_promotion_allowed": False,
            "investment_signal_allowed": False,
            "llm_narrative_generation_allowed": False,
        },
        "topics": topics,
    }


def render_live_narrative_review_page_html(page: dict[str, Any]) -> str:
    summary = _mapping(page.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>真实叙事复核页</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>真实叙事复核页</h1>",
            '<section class="summary">',
            _html_kv("生成时间", page.get("generated_at")),
            _html_kv("Gateway", page.get("base_url") or "未配置"),
            _html_kv("主题数", summary.get("topic_count", 0)),
            _html_kv("候选叙事", summary.get("candidate_count", 0)),
            _html_kv("来源事件", summary.get("source_event_count", 0)),
            _html_kv("缺失来源", summary.get("missing_source_kind_count", 0)),
            _html_kv("降级来源", summary.get("degraded_source_kind_count", 0)),
            "<p>本页只展示 Gateway 返回的真实来源事件和缺口状态，不会自动升级为可信叙事，也不提供投资建议。</p>",
            "</section>",
            "".join(_topic_section(_mapping(topic)) for topic in _list(page.get("topics"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _topic_payload(result: dict[str, Any]) -> dict[str, Any]:
    topic_name = str(result.get("topic_name") or result.get("query") or "")
    query = str(result.get("query") or topic_name)
    source_results = [_mapping(item) for item in _list(result.get("source_results"))]
    evidence_events = _evidence_events(source_results)
    candidate = _candidate(topic_name=topic_name, query=query, events=evidence_events)
    return {
        "topic_id": _slug(topic_name),
        "topic_name": topic_name,
        "query": query,
        "status": "candidate_available" if candidate else "no_usable_rows",
        "candidate": candidate,
        "evidence_events": evidence_events,
        "source_kind_states": {
            str(source_result.get("source_kind") or "unknown"): _source_kind_state(source_result)
            for source_result in source_results
        },
        "missing_or_degraded_source_kinds": [
            _gap_row(source_result)
            for source_result in source_results
            if _is_gap(source_result)
        ],
    }


def _candidate(
    *, topic_name: str, query: str, events: list[dict[str, Any]]
) -> dict[str, Any] | None:
    if not events:
        return None
    return {
        "candidate_id": _stable_id("LIVE_CAND", topic_name, query),
        "candidate_name": topic_name,
        "summary": f"Gateway 返回 {len(events)} 条来源事件，作为待人工复核的候选叙事。",
        "candidate_state": "candidate_untrusted",
        "supporting_source_event_count": len(events),
        "source_kinds": _unique(str(event.get("source_kind") or "") for event in events),
        "best_trust_tier": _best_trust_tier(events),
        "next_operator_action": _next_operator_action(events),
        "trusted_promotion_allowed": False,
        "investment_signal_allowed": False,
    }


def _evidence_events(source_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_result in source_results:
        source_kind = str(source_result.get("source_kind") or "")
        result_degradation = _degradation_codes(source_result.get("degradation_events"))
        for row in _list(source_result.get("rows")):
            if not isinstance(row, dict):
                continue
            source_url = str(row.get("source_url") or "")
            title = str(row.get("title") or "")
            if not source_url or not title:
                continue
            row_degradation = _degradation_codes(row.get("degradation_events"))
            rows.append(
                {
                    "source_event_id": str(row.get("source_event_id") or row.get("event_id") or ""),
                    "title": title,
                    "source_url": source_url,
                    "domain": _domain(source_url),
                    "source_kind": str(row.get("source_kind") or source_kind),
                    "trust_tier": str(row.get("trust_tier") or "candidate_untrusted"),
                    "source_quality": str(row.get("source_quality") or "unknown"),
                    "event_time": str(row.get("event_time") or ""),
                    "provider": str(row.get("provider") or row.get("source_provider") or ""),
                    "retention_policy": str(row.get("retention_policy") or ""),
                    "license_scope": str(row.get("license_scope") or ""),
                    "metadata_only": bool(row.get("metadata_only", True)),
                    "degradation_events": _unique(row_degradation + result_degradation),
                }
            )
    return sorted(rows, key=lambda row: (str(row.get("event_time") or ""), str(row.get("title") or "")), reverse=True)


def _source_kind_state(source_result: dict[str, Any]) -> dict[str, Any]:
    rows = _list(source_result.get("rows"))
    status = str(source_result.get("status") or ("completed" if rows else "missing"))
    return {
        "source_kind": str(source_result.get("source_kind") or "unknown"),
        "status": status,
        "row_count": int(source_result.get("row_count") or len(rows)),
        "reason": _gap_reason(source_result),
        "degradation_events": _degradation_codes(source_result.get("degradation_events")),
    }


def _gap_row(source_result: dict[str, Any]) -> dict[str, Any]:
    state = _source_kind_state(source_result)
    return {
        "source_kind": state["source_kind"],
        "status": state["status"],
        "row_count": state["row_count"],
        "reason": state["reason"],
    }


def _is_gap(source_result: dict[str, Any]) -> bool:
    rows = _list(source_result.get("rows"))
    status = str(source_result.get("status") or "")
    return status != "completed" or not rows


def _gap_reason(source_result: dict[str, Any]) -> str:
    degradation_codes = _degradation_codes(source_result.get("degradation_events"))
    if degradation_codes:
        return degradation_codes[0]
    failure_reason = str(source_result.get("failure_reason") or "")
    if failure_reason:
        return failure_reason
    if not _list(source_result.get("rows")):
        return "NO_ROWS"
    return ""


def _best_trust_tier(events: list[dict[str, Any]]) -> str:
    priority = {
        "trusted_fact": 0,
        "official_primary": 1,
        "context_only": 2,
        "heat_signal_only": 3,
        "candidate_untrusted": 4,
    }
    return sorted(
        (str(event.get("trust_tier") or "candidate_untrusted") for event in events),
        key=lambda value: priority.get(value, 9),
    )[0]


def _next_operator_action(events: list[dict[str, Any]]) -> str:
    if any(str(event.get("degradation_events") or "") not in {"", "[]"} for event in events):
        return "request_more_evidence"
    if any(str(event.get("trust_tier") or "") in {"trusted_fact", "official_primary"} for event in events):
        return "inspect_evidence"
    return "request_more_evidence"


def _topic_section(topic: dict[str, Any]) -> str:
    candidate = _mapping(topic.get("candidate"))
    gaps = _list(topic.get("missing_or_degraded_source_kinds"))
    return "\n".join(
        [
            f'<section class="topic" id="{_html_text(topic.get("topic_id"))}">',
            f"<h2>{_html_text(topic.get('topic_name'))}</h2>",
            '<div class="topic-grid">',
            '<div class="panel">',
            "<h3>候选叙事</h3>",
            _candidate_html(candidate),
            "</div>",
            '<div class="panel">',
            "<h3>缺口状态</h3>",
            _gap_table(gaps),
            "</div>",
            "</div>",
            _event_table(_list(topic.get("evidence_events"))),
            "</section>",
        ]
    )


def _candidate_html(candidate: dict[str, Any]) -> str:
    if not candidate:
        return "<p>当前主题没有可用来源事件，暂不生成候选叙事。</p>"
    return "".join(
        [
            _html_kv("名称", candidate.get("candidate_name")),
            _html_kv("摘要", candidate.get("summary")),
            _html_kv("状态", candidate.get("candidate_state")),
            _html_kv("下一步", candidate.get("next_operator_action")),
            _html_kv("最佳信任层级", candidate.get("best_trust_tier")),
        ]
    )


def _event_table(events: list[Any]) -> str:
    if not events:
        return "<section><h3>来源事件</h3><p>暂无可展示的来源事件。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in (
            "标题",
            "URL",
            "来源类型",
            "信任层级",
            "来源质量",
            "时间",
            "下一步证据",
        )
    )
    body = "".join(_event_row(_mapping(event)) for event in events)
    return f"<section><h3>来源事件</h3><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _event_row(event: dict[str, Any]) -> str:
    source_url = str(event.get("source_url") or "")
    return (
        "<tr>"
        f"<td>{_html_text(event.get('title'))}</td>"
        f'<td><a href="{_html_text(source_url)}">{_html_text(source_url)}</a></td>'
        f"<td><code>{_html_text(event.get('source_kind'))}</code></td>"
        f"<td><code>{_html_text(event.get('trust_tier'))}</code></td>"
        f"<td><code>{_html_text(event.get('source_quality'))}</code></td>"
        f"<td>{_html_text(event.get('event_time'))}</td>"
        f"<td>打开链接并核对原始来源上下文</td>"
        "</tr>"
    )


def _gap_table(gaps: list[Any]) -> str:
    if not gaps:
        return "<p>当前主题没有显式缺失或降级来源。</p>"
    rows = "".join(
        "<tr>"
        f"<td><code>{_html_text(_mapping(gap).get('source_kind'))}</code></td>"
        f"<td>{_html_text(_mapping(gap).get('status'))}</td>"
        f"<td>{_html_text(_mapping(gap).get('row_count'))}</td>"
        f"<td>{_html_text(_mapping(gap).get('reason'))}</td>"
        "</tr>"
        for gap in gaps
    )
    return (
        "<table><thead><tr><th>来源类型</th><th>状态</th><th>行数</th><th>原因</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1200px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; letter-spacing: 0; }
h2 { font-size: 23px; margin: 28px 0 14px; letter-spacing: 0; }
h3 { font-size: 17px; margin: 0 0 12px; letter-spacing: 0; }
.summary, .panel { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
.topic { margin-top: 24px; }
.topic-grid { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr); gap: 14px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; table-layout: fixed; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; overflow-wrap: anywhere; }
th { background: #eef2f7; color: #323f4b; }
code { background: #eef2f7; border-radius: 4px; padding: 1px 4px; }
a { color: #1d4ed8; }
@media (max-width: 800px) { .topic-grid { grid-template-columns: 1fr; } .page { padding: 20px 12px 36px; } }
"""


def _degradation_codes(value: Any) -> list[str]:
    codes: list[str] = []
    for item in _list(value):
        if isinstance(item, dict):
            codes.append(str(item.get("code") or item.get("message") or item))
        else:
            codes.append(str(item))
    return _unique(codes)


def _domain(url: str) -> str:
    return urlparse(url).netloc


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in slug.split("-") if part) or "topic"


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
