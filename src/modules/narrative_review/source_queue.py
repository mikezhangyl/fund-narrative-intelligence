from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

SUPPORT_CLASS_LABELS = {
    "official_fact_backed": "官方事实支撑候选",
    "context_only": "上下文候选",
    "heat_signal_only": "热度信号候选",
    "candidate_untrusted": "未验证候选",
}
PRIORITY_ORDER = {"needs_triage": 0, "high": 1, "medium": 2, "low": 3}


def build_source_candidate_review_queue(
    *,
    candidate_inbox: dict[str, Any],
    fresh_digest: dict[str, Any] | None = None,
    generated_at: str | None = None,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    active_filters = _clean_filters(filters)
    digest_by_key = _digest_items_by_key(fresh_digest or {})
    all_rows = [
        _queue_row(candidate, digest_by_key=digest_by_key)
        for candidate in _list(candidate_inbox.get("candidates"))
        if isinstance(candidate, dict)
    ]
    sorted_rows = sorted(
        all_rows,
        key=lambda row: (
            PRIORITY_ORDER.get(str(row.get("review_priority") or ""), 99),
            str(row.get("newest_event_time") or ""),
            str(row.get("candidate_id") or ""),
        ),
    )
    visible_rows = [row for row in sorted_rows if _matches_filters(row, active_filters)]
    return {
        "version": "source-candidate-review-queue-v1",
        "generated_at": generated_at or _utc_now(),
        "fixture_mode": bool(candidate_inbox.get("fixture_mode", True)),
        "status": candidate_inbox.get("status", "ok"),
        "filters": active_filters,
        "summary": _summary(all_rows, visible_rows),
        "contract": {
            "trusted_promotion_allowed": False,
            "llm_clustering_allowed": False,
            "direct_external_source_calls": False,
            "investment_recommendation_allowed": False,
        },
        "rows": visible_rows,
    }


def render_source_candidate_review_queue_html(queue: dict[str, Any]) -> str:
    summary = _mapping(queue.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>来源候选叙事复核队列</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>来源候选叙事复核队列</h1>",
            '<section class="summary">',
            _html_kv("总候选数", summary.get("total_count", 0)),
            _html_kv("当前显示", summary.get("visible_count", 0)),
            _html_kv("官方支撑", summary.get("official_backed_count", 0)),
            _html_kv("上下文候选", summary.get("context_only_count", 0)),
            _html_kv("热度候选", summary.get("heat_only_count", 0)),
            _html_kv("降级候选", summary.get("degraded_count", 0)),
            "<p>本队列用于人工复核，不会自动升级为可信叙事，也不提供投资建议。</p>",
            "</section>",
            _rows_table(_list(queue.get("rows"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _queue_row(
    candidate: dict[str, Any], *, digest_by_key: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    candidate_id = str(candidate.get("stable_candidate_id") or candidate.get("candidate_id") or "")
    narrative_key = str(candidate.get("narrative_key") or candidate_id)
    digest_item = digest_by_key.get(narrative_key, {})
    support_class = str(candidate.get("support_class") or "candidate_untrusted")
    degradation_flags = _strings(candidate.get("degradation_events"))
    source_kind_mix = [_source_mix_row(row) for row in _list(candidate.get("source_mix"))]
    symbols = _symbols_from_digest(digest_item)
    markets = _markets_for_symbols(symbols)
    best_trust_tier = str(
        _mapping(candidate.get("source_quality_metadata")).get("best_trust_tier")
        or candidate.get("trust_state")
        or "candidate_untrusted"
    )
    return {
        "candidate_id": candidate_id,
        "title": str(candidate.get("display_name") or candidate.get("title") or narrative_key),
        "topic": narrative_key,
        "candidate_state": str(candidate.get("candidate_status") or "candidate_untrusted"),
        "freshness_state": str(digest_item.get("candidate_state") or "unknown"),
        "source_event_count": _int(candidate.get("event_count")),
        "source_kind_mix": source_kind_mix,
        "newest_event_time": str(candidate.get("newest_event_time") or ""),
        "related_entities": {
            "symbols": symbols,
            "markets": markets,
        },
        "trust_tier_summary": {
            "best_trust_tier": best_trust_tier,
            "source_quality_labels": _strings(
                _mapping(candidate.get("source_quality_metadata")).get("source_quality_labels")
                or candidate.get("trust_labels")
            ),
            "support_class": support_class,
        },
        "degradation_flags": degradation_flags,
        "review_priority": _review_priority(
            support_class=support_class,
            degradation_flags=degradation_flags,
        ),
        "trusted_promotion_allowed": False,
        "support_class_label": SUPPORT_CLASS_LABELS.get(support_class, support_class),
        "artifact_links": {
            "evidence_detail_json": f"candidate_evidence/{candidate_id}.json",
            "evidence_detail_html": f"candidate_evidence/{candidate_id}.html",
        },
        "evidence_links": [
            link for link in _list(candidate.get("evidence_links")) if isinstance(link, dict)
        ],
    }


def _summary(all_rows: list[dict[str, Any]], visible_rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_count": len(all_rows),
        "visible_count": len(visible_rows),
        "official_backed_count": _support_count(all_rows, "official_fact_backed"),
        "context_only_count": _support_count(all_rows, "context_only"),
        "heat_only_count": _support_count(all_rows, "heat_signal_only"),
        "degraded_count": sum(1 for row in all_rows if row.get("degradation_flags")),
        "trusted_count": sum(1 for row in all_rows if row.get("candidate_state") == "trusted"),
    }


def _matches_filters(row: dict[str, Any], filters: dict[str, str]) -> bool:
    return all(
        [
            not filters.get("source_kind") or _has_source_kind(row, filters["source_kind"]),
            not filters.get("trust_tier")
            or row["trust_tier_summary"]["best_trust_tier"] == filters["trust_tier"],
            not filters.get("freshness_state")
            or row.get("freshness_state") == filters["freshness_state"],
            not filters.get("market")
            or filters["market"] in row.get("related_entities", {}).get("markets", []),
            not filters.get("candidate_state")
            or row.get("candidate_state") == filters["candidate_state"],
        ]
    )


def _has_source_kind(row: dict[str, Any], source_kind: str) -> bool:
    return any(
        item.get("source_kind") == source_kind
        for item in _list(row.get("source_kind_mix"))
        if isinstance(item, dict)
    )


def _review_priority(*, support_class: str, degradation_flags: list[str]) -> str:
    if degradation_flags:
        return "needs_triage"
    if support_class == "official_fact_backed":
        return "high"
    if support_class == "context_only":
        return "medium"
    return "low"


def _digest_items_by_key(digest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("narrative_key") or ""): item
        for item in _list(digest.get("items"))
        if isinstance(item, dict) and str(item.get("narrative_key") or "")
    }


def _source_mix_row(row: Any) -> dict[str, Any]:
    data = _mapping(row)
    return {
        "source_kind": str(data.get("source_kind") or "unknown"),
        "event_count": _int(data.get("event_count")),
    }


def _symbols_from_digest(digest_item: dict[str, Any]) -> list[str]:
    stocks = _list(_mapping(digest_item.get("entities")).get("stocks"))
    symbols = [
        str(_mapping(stock).get("stock_code") or _mapping(stock).get("ticker") or "").upper()
        for stock in stocks
    ]
    return _unique(symbol for symbol in symbols if symbol)


def _markets_for_symbols(symbols: list[str]) -> list[str]:
    markets = []
    for symbol in symbols:
        if symbol.endswith((".SH", ".SZ")) or symbol[:1].isdigit():
            markets.append("CN")
        elif symbol.isalpha():
            markets.append("US")
        else:
            markets.append("global")
    return _unique(markets)


def _support_count(rows: list[dict[str, Any]], support_class: str) -> int:
    return sum(
        1
        for row in rows
        if row.get("trust_tier_summary", {}).get("support_class") == support_class
    )


def _clean_filters(filters: dict[str, str] | None) -> dict[str, str]:
    if not filters:
        return {}
    return {key: str(value) for key, value in filters.items() if str(value or "")}


def _rows_table(rows: list[Any]) -> str:
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in (
            "候选叙事",
            "候选状态",
            "新鲜度",
            "支撑类型",
            "来源",
            "实体",
            "信任摘要",
            "优先级",
            "证据",
        )
    )
    body = "".join(_row_html(_mapping(row)) for row in rows)
    return f"<section><h2>队列</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _row_html(row: dict[str, Any]) -> str:
    links = _mapping(row.get("artifact_links"))
    evidence_href = str(links.get("evidence_detail_html") or "")
    evidence = (
        f'<a href="{_html_text(evidence_href)}">查看证据</a>'
        if evidence_href
        else "暂无证据详情"
    )
    entities = _mapping(row.get("related_entities"))
    source_kinds = ", ".join(
        str(item.get("source_kind") or "")
        for item in _list(row.get("source_kind_mix"))
        if isinstance(item, dict)
    )
    return (
        "<tr>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(row.get('candidate_state'))}</td>"
        f"<td>{_html_text(row.get('freshness_state'))}</td>"
        f"<td>{_html_text(row.get('support_class_label'))}</td>"
        f"<td>{_html_text(source_kinds)}</td>"
        f"<td>{_html_text(', '.join(_strings(entities.get('symbols'))))}</td>"
        f"<td>{_html_text(_mapping(row.get('trust_tier_summary')).get('best_trust_tier'))}</td>"
        f"<td>{_html_text(row.get('review_priority'))}</td>"
        f"<td>{evidence}</td>"
        "</tr>"
    )


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
a { color: #1d4ed8; }
"""


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
