from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from html import escape
from typing import Any

SUPPORTED_STATES = ["new", "accelerating", "persistent", "cooling", "disputed"]
EXPECTED_GATEWAY_SOURCE_KINDS = [
    "official_filings",
    "official_disclosures",
    "official_sources",
    "news_context",
    "open_news_index",
    "industry_media",
    "social_heat",
]
OFFICIAL_SOURCE_KINDS = {"official_filings", "official_disclosures", "official_sources"}
CONTEXT_SOURCE_KINDS = {"news_context", "open_news_index", "industry_media"}
CRAWLER_REQUIRED_FIELDS = [
    "max_concurrency",
    "per_domain_pacing_seconds",
    "timeout_seconds",
    "retry_backoff_seconds",
    "cache_ttl_seconds",
    "content_hash",
    "parser_version",
    "robots_tos_metadata",
    "failure_reason",
]


def build_fresh_narrative_digest(
    *,
    source_events: list[dict[str, Any]],
    window_start: str,
    window_end: str,
    generated_at: str | None = None,
    fixture_mode: bool = True,
    source_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    deduped_events = _dedupe_events(source_events)
    groups = _group_events_by_narrative(deduped_events)
    source_coverage = _source_coverage(source_results)
    items = [
        _digest_item(
            narrative_key=narrative_key,
            events=events,
            window_start=window_start,
            window_end=window_end,
        )
        for narrative_key, events in sorted(groups.items())
    ]
    coverage_gaps = _list(source_coverage.get("gaps"))
    summary = {
        "raw_event_count": len(source_events),
        "deduped_event_count": len(deduped_events),
        "digest_item_count": len(items),
        "degraded_item_count": sum(1 for item in items if item["candidate_state"] == "disputed"),
    }
    if source_results is not None:
        summary |= {
            "coverage_gap_count": len(coverage_gaps),
            "degraded_input_count": sum(
                1 for gap in coverage_gaps if gap["coverage_status"] == "degraded"
            ),
        }
    return {
        "version": "fresh-narrative-digest-v1",
        "generated_at": generated_at or _utc_now(),
        "status": "degraded" if coverage_gaps else "ok",
        "fixture_mode": fixture_mode,
        "window": {
            "start": window_start,
            "end": window_end,
        },
        "summary": summary,
        "source_coverage": source_coverage,
        "daily_digest_sections": _daily_digest_sections(items, coverage_gaps),
        "contract": {
            "supported_candidate_states": SUPPORTED_STATES,
            "trading_claims_allowed": False,
            "provider_access_allowed": False,
            "mode_support": ["fixture", "live_gateway_probe"],
        },
        "entity_resolution_contract": {
            "stable_entity_id_format": "<ENTITY_TYPE>_<CANONICAL_CODE_OR_HASH>",
            "alias_inputs": ["ticker", "stock_code", "name_zh", "name_en", "provider_entity_id"],
            "ambiguous_entity_policy": "keep_candidate_with_alias_context",
        },
        "dedupe_contract": {
            "stable_id_inputs": [
                "source_event_id",
                "dedupe_key",
                "provider",
                "normalized_title",
                "published_at",
            ],
            "near_duplicate_policy": "same provider/title/day or explicit dedupe_key",
        },
        "crawler_adapter_contract": {
            "network_required_for_fixture_tests": False,
            "dynamic_browser_rendering_allowed": False,
            "required_fields": CRAWLER_REQUIRED_FIELDS,
            "structured_failure_reasons": [
                "robots_tos_not_approved",
                "rate_limited",
                "timeout",
                "parse_error",
                "unsupported_dynamic_rendering",
                "permission_missing",
            ],
        },
        "items": items,
    }


def render_fresh_narrative_digest_html(digest: dict[str, Any]) -> str:
    summary = _mapping(digest.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>今日叙事监控摘要</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>今日叙事监控摘要</h1>",
            '<section class="summary">',
            _html_kv("状态", digest.get("status")),
            _html_kv("原始事件", summary.get("raw_event_count", 0)),
            _html_kv("去重事件", summary.get("deduped_event_count", 0)),
            _html_kv("摘要项", summary.get("digest_item_count", 0)),
            "<p>本摘要用于叙事监控和证据复核，不生成交易建议。</p>",
            "</section>",
            _items_table(_list(digest.get("items"))),
            _coverage_table(_list(_mapping(digest.get("source_coverage")).get("gaps"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def build_narrative_candidate_inbox(
    *,
    source_events: list[dict[str, Any]],
    generated_at: str | None = None,
    fixture_mode: bool = True,
    source_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    deduped_events = _dedupe_events(source_events)
    groups = _group_events_by_narrative(deduped_events)
    source_coverage = _source_coverage(source_results)
    candidates = [
        _candidate_item(narrative_key=narrative_key, events=events)
        for narrative_key, events in sorted(groups.items())
    ]
    coverage_gaps = _list(source_coverage.get("gaps"))
    return {
        "version": "narrative-candidate-inbox-v1",
        "generated_at": generated_at or _utc_now(),
        "status": "degraded" if coverage_gaps else "ok",
        "fixture_mode": fixture_mode,
        "summary": {
            "raw_event_count": len(source_events),
            "deduped_event_count": len(deduped_events),
            "candidate_count": len(candidates),
            "coverage_gap_count": len(coverage_gaps),
        },
        "contract": {
            "provider_access_allowed": False,
            "promotion_allowed": False,
            "llm_clustering_allowed": False,
            "direct_external_source_calls": False,
        },
        "source_coverage": source_coverage,
        "candidates": candidates,
    }


def render_narrative_candidate_inbox_html(inbox: dict[str, Any]) -> str:
    summary = _mapping(inbox.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>候选叙事收件箱</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>候选叙事收件箱</h1>",
            '<section class="summary">',
            _html_kv("状态", inbox.get("status")),
            _html_kv("候选数", summary.get("candidate_count", 0)),
            _html_kv("覆盖缺口", summary.get("coverage_gap_count", 0)),
            "<p>候选项用于人工复核，不会自动升级为可信叙事，也不生成投资建议。</p>",
            "</section>",
            _candidate_table(_list(inbox.get("candidates"))),
            _coverage_table(_list(_mapping(inbox.get("source_coverage")).get("gaps"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def extract_source_events_from_probe(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in _list(payload.get("source_results")):
        result_map = _mapping(result)
        source_kind = str(result_map.get("source_kind") or "")
        result_degradation = _strings(result_map.get("degradation_events"))
        for row in _list(result_map.get("rows")):
            if not isinstance(row, dict):
                continue
            row_degradation = _strings(row.get("degradation_events"))
            rows.append(
                {
                    **row,
                    "source_kind": str(row.get("source_kind") or source_kind),
                    "degradation_events": _unique(row_degradation + result_degradation),
                }
            )
    if rows:
        return rows
    return [row for row in _list(payload.get("source_events")) if isinstance(row, dict)]


def _digest_item(
    *,
    narrative_key: str,
    events: list[dict[str, Any]],
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    in_window = [event for event in events if _in_window(_event_time(event), window_start, window_end)]
    degradation_events = _unique(
        event_degradation
        for event in events
        for event_degradation in _strings(event.get("degradation_events"))
    )
    state = _candidate_state(events, in_window, degradation_events)
    source_quality = _source_quality_metadata(events)
    source_kinds = _unique(_source_kind(event) for event in events)
    return {
        "stable_digest_id": _stable_id("NDIG", narrative_key),
        "narrative_key": narrative_key,
        "display_name": _display_name(events, narrative_key),
        "candidate_state": state,
        "reason_for_inclusion": _reason_for_inclusion(state, len(in_window)),
        "event_count": len(events),
        "in_window_event_count": len(in_window),
        "entities": {
            "stocks": _stock_entities(events),
            "concepts": [{"stable_entity_id": _stable_id("CONCEPT", narrative_key), "name": _display_name(events, narrative_key)}],
        },
        "source_kinds": source_kinds,
        "evidence_links": _evidence_links(events),
        "source_quality_metadata": source_quality,
        "degradation_events": degradation_events,
        "trust_state": source_quality["best_trust_tier"],
    }


def _candidate_state(
    events: list[dict[str, Any]],
    in_window: list[dict[str, Any]],
    degradation_events: list[str],
) -> str:
    if degradation_events:
        return "disputed"
    if len(in_window) >= 3:
        return "accelerating"
    if len(in_window) == 2:
        return "persistent"
    if len(in_window) == 1:
        return "new"
    return "cooling" if events else "new"


def _reason_for_inclusion(state: str, in_window_count: int) -> str:
    if state == "disputed":
        return "Source events include degradation or conflicting-claim markers."
    if in_window_count == 1:
        return "1 source event in the selected window."
    return f"{in_window_count} source events in the selected window."


def _candidate_item(*, narrative_key: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    source_quality = _source_quality_metadata(events)
    support_class = _support_class(events, source_quality["best_trust_tier"])
    return {
        "stable_candidate_id": _stable_id("CAND", narrative_key),
        "narrative_key": narrative_key,
        "display_name": _display_name(events, narrative_key),
        "candidate_status": "candidate_untrusted",
        "support_class": support_class,
        "event_count": len(events),
        "source_mix": _source_mix(events),
        "newest_event_time": max((_event_time(event) for event in events), default=""),
        "trust_labels": source_quality["source_quality_labels"],
        "trust_state": "candidate_untrusted",
        "promotion_allowed": False,
        "why_untrusted": _why_untrusted(support_class),
        "evidence_links": _evidence_links(events),
        "source_quality_metadata": source_quality,
        "degradation_events": _unique(
            event_degradation
            for event in events
            for event_degradation in _strings(event.get("degradation_events"))
        ),
    }


def _support_class(events: list[dict[str, Any]], best_trust_tier: str) -> str:
    source_kinds = {_source_kind(event) for event in events}
    if source_kinds == {"social_heat"} or best_trust_tier == "heat_signal_only":
        return "heat_signal_only"
    if any(source_kind in OFFICIAL_SOURCE_KINDS for source_kind in source_kinds):
        return "official_fact_backed"
    if any(source_kind in CONTEXT_SOURCE_KINDS for source_kind in source_kinds):
        return "context_only"
    return "candidate_untrusted"


def _why_untrusted(support_class: str) -> str:
    if support_class == "official_fact_backed":
        return "官方事实可以支撑候选来源，但仍需人工复核后才能进入可信叙事。"
    if support_class == "heat_signal_only":
        return "热度只能说明讨论变化，不能单独证明事实或升级信任。"
    if support_class == "context_only":
        return "开放新闻/行业上下文只能作为候选线索，不能单独升级为可信事实。"
    return "候选线索缺少足够来源质量和复核证据。"


def _source_mix(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for event in events:
        source_kind = _source_kind(event) or "unknown"
        counts[source_kind] = counts.get(source_kind, 0) + 1
    return [
        {"source_kind": source_kind, "event_count": counts[source_kind]}
        for source_kind in sorted(counts)
    ]


def _source_coverage(source_results: list[dict[str, Any]] | None) -> dict[str, Any]:
    if source_results is None:
        return {
            "expected_source_kinds": EXPECTED_GATEWAY_SOURCE_KINDS,
            "observed_source_kinds": [],
            "gaps": [],
        }
    by_kind = {
        str(result.get("source_kind") or ""): _mapping(result)
        for result in source_results
        if str(result.get("source_kind") or "")
    }
    gaps = [
        gap
        for source_kind in EXPECTED_GATEWAY_SOURCE_KINDS
        if (gap := _coverage_gap_for_source_kind(source_kind, by_kind.get(source_kind))) is not None
    ]
    return {
        "expected_source_kinds": EXPECTED_GATEWAY_SOURCE_KINDS,
        "observed_source_kinds": sorted(by_kind),
        "gaps": gaps,
    }


def _coverage_gap_for_source_kind(
    source_kind: str, result: dict[str, Any] | None
) -> dict[str, Any] | None:
    if result is None:
        return {
            "source_kind": source_kind,
            "coverage_status": "missing",
            "reason": "Gateway probe did not include this source kind.",
            "degradation_events": ["GATEWAY_SOURCE_KIND_MISSING"],
        }
    row_count = _result_row_count(result)
    degradation_events = _strings(result.get("degradation_events"))
    status = str(result.get("status") or "")
    if degradation_events or status == "degraded":
        return {
            "source_kind": source_kind,
            "coverage_status": "degraded",
            "reason": "Gateway returned structured degraded input for this source kind.",
            "degradation_events": degradation_events,
        }
    if status in {"failed", "blocked"}:
        return {
            "source_kind": source_kind,
            "coverage_status": "blocked",
            "reason": "Gateway source kind failed or is blocked.",
            "degradation_events": degradation_events,
        }
    if row_count <= 0:
        return {
            "source_kind": source_kind,
            "coverage_status": "missing",
            "reason": "Gateway probe returned no source-event rows for this source kind.",
            "degradation_events": ["NO_SOURCE_EVENTS"],
        }
    return None


def _result_row_count(result: dict[str, Any]) -> int:
    explicit = result.get("row_count")
    if isinstance(explicit, int):
        return explicit
    if isinstance(explicit, str) and explicit.isdigit():
        return int(explicit)
    return len(_list(result.get("rows")))


def _daily_digest_sections(
    items: list[dict[str, Any]], coverage_gaps: list[Any]
) -> dict[str, list[str]]:
    sections = {
        "new": [],
        "heating": [],
        "persistent": [],
        "cooling": [],
        "disputed": [],
        "degraded_input": [
            str(_mapping(gap).get("source_kind") or "")
            for gap in coverage_gaps
            if _mapping(gap).get("coverage_status") in {"degraded", "blocked", "missing"}
        ],
    }
    state_to_section = {"accelerating": "heating"}
    for item in items:
        state = str(item.get("candidate_state") or "")
        section = state_to_section.get(state, state)
        if section in sections:
            sections[section].append(str(item.get("narrative_key") or ""))
    return sections


def _dedupe_events(source_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in source_events:
        key = _dedupe_key(event)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def _dedupe_key(event: dict[str, Any]) -> str:
    explicit = str(event.get("dedupe_key") or "")
    if explicit:
        return f"dedupe:{explicit}"
    return "|".join(
        [
            str(event.get("provider") or ""),
            _normalize_title(str(event.get("title") or "")),
            str(event.get("published_at") or event.get("event_time") or ""),
        ]
    )


def _group_events_by_narrative(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        label = _first_string(event.get("narrative_hints")) or _first_string(event.get("topics")) or "uncategorized"
        groups.setdefault(_slug(label), []).append(event)
    return groups


def _source_quality_metadata(events: list[dict[str, Any]]) -> dict[str, Any]:
    trust_order = ["trusted_fact", "context_only", "heat_signal_only", "candidate_untrusted", "blocked"]
    tiers = [_trust_tier(event) for event in events]
    best = min(tiers, key=lambda tier: trust_order.index(tier) if tier in trust_order else 99) if tiers else "candidate_untrusted"
    labels = _unique(_source_quality_label(event) for event in events)
    return {
        "best_trust_tier": best,
        "source_quality_labels": labels,
        "license_scopes": _unique(str(event.get("license_scope") or "") for event in events if event.get("license_scope")),
        "retention_policies": _unique(str(event.get("retention_policy") or "") for event in events if event.get("retention_policy")),
    }


def _trust_tier(event: dict[str, Any]) -> str:
    source_kind = _source_kind(event)
    if source_kind == "social_heat":
        return "heat_signal_only"
    raw = str(event.get("source_trust_tier") or _mapping(event.get("meta")).get("trust_tier") or "candidate_untrusted")
    if not source_kind:
        return raw or "candidate_untrusted"
    if raw == "trusted_fact" and source_kind not in OFFICIAL_SOURCE_KINDS:
        return "context_only" if source_kind in CONTEXT_SOURCE_KINDS else "candidate_untrusted"
    if source_kind in CONTEXT_SOURCE_KINDS and raw in {"candidate_untrusted", ""}:
        return "context_only"
    return raw or "candidate_untrusted"


def _source_kind(event: dict[str, Any]) -> str:
    return str(event.get("source_kind") or _mapping(event.get("meta")).get("source_kind") or "")


def _source_quality_label(event: dict[str, Any]) -> str:
    value = event.get("source_quality")
    if isinstance(value, dict):
        return str(value.get("label") or _trust_tier(event))
    if isinstance(value, str) and value:
        return _trust_tier(event) if _source_kind(event) in CONTEXT_SOURCE_KINDS | {"social_heat"} else value
    return _trust_tier(event)


def _stock_entities(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    entities: dict[str, dict[str, str]] = {}
    for event in events:
        for stock in _list(event.get("mentioned_stocks")):
            row = _mapping(stock)
            code = str(row.get("stock_code") or row.get("ticker") or "").upper()
            if not code:
                continue
            entities[code] = {
                "stable_entity_id": f"STOCK_{code}",
                "stock_code": code,
                "display_name": str(row.get("stock_name") or code),
            }
    return [entities[code] for code in sorted(entities)]


def _evidence_links(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    links = []
    for event in events:
        source_event_id = str(event.get("source_event_id") or event.get("event_id") or "")
        links.append(
            {
                "source_event_id": source_event_id,
                "title": str(event.get("title") or ""),
                "provider": str(event.get("provider") or ""),
                "event_time": _event_time(event),
            }
        )
    return links


def _display_name(events: list[dict[str, Any]], fallback: str) -> str:
    for event in events:
        label = _first_string(event.get("narrative_hints")) or _first_string(event.get("topics"))
        if label:
            return label
    return fallback


def _event_time(event: dict[str, Any]) -> str:
    return str(event.get("published_at") or event.get("event_time") or "")


def _in_window(value: str, window_start: str, window_end: str) -> bool:
    current = _parse_datetime(value)
    start = _parse_datetime(window_start)
    end = _parse_datetime(window_end)
    if current is None or start is None or end is None:
        return False
    return start <= current <= end


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.fromisoformat(value).replace(tzinfo=UTC)
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}_{digest}"


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or _stable_id("NARRATIVE", value).lower()


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _items_table(items: list[Any]) -> str:
    rows = [_mapping(item) for item in items]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("叙事", "状态", "事件", "来源质量", "原因", "证据")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('display_name'))}</td>"
        f"<td>{_html_text(row.get('candidate_state'))}</td>"
        f"<td>{_html_text(row.get('event_count'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_quality_metadata')).get('best_trust_tier'))}</td>"
        f"<td>{_html_text(row.get('reason_for_inclusion'))}</td>"
        f"<td>{_html_text(', '.join(link.get('source_event_id', '') for link in _list(row.get('evidence_links'))))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>摘要项</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _candidate_table(candidates: list[Any]) -> str:
    rows = [_mapping(candidate) for candidate in candidates]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("候选叙事", "支撑类型", "事件数", "信任状态", "为何未升级", "证据")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('display_name'))}</td>"
        f"<td>{_html_text(_display_support_class(row.get('support_class')))}</td>"
        f"<td>{_html_text(row.get('event_count'))}</td>"
        f"<td>{_html_text(row.get('trust_state'))}</td>"
        f"<td>{_html_text(row.get('why_untrusted'))}</td>"
        f"<td>{_html_text(', '.join(link.get('source_event_id', '') for link in _list(row.get('evidence_links'))))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>候选项</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _coverage_table(gaps: list[Any]) -> str:
    rows = [_mapping(gap) for gap in gaps]
    if not rows:
        return "<section><h2>输入缺口</h2><p>没有 Gateway 输入缺口。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("来源类型", "状态", "原因", "降级事件")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(_display_source_kind(row.get('source_kind')))}</td>"
        f"<td>{_html_text(row.get('coverage_status'))}</td>"
        f"<td>{_html_text(row.get('reason'))}</td>"
        f"<td>{_html_text(', '.join(_strings(row.get('degradation_events'))))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>输入缺口</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _display_support_class(value: Any) -> str:
    mapping = {
        "official_fact_backed": "官方事实支撑候选",
        "context_only": "上下文候选",
        "heat_signal_only": "热度信号候选",
        "candidate_untrusted": "未验证候选",
    }
    return mapping.get(str(value or ""), str(value or ""))


def _display_source_kind(value: Any) -> str:
    mapping = {
        "official_filings": "官方披露文件",
        "official_disclosures": "官方公告披露",
        "official_sources": "政策/监管/行业官方来源",
        "news_context": "新闻上下文",
        "open_news_index": "开放新闻索引",
        "industry_media": "行业媒体",
        "social_heat": "社交热度",
    }
    return mapping.get(str(value or ""), str(value or ""))


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


def _first_string(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return ""


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


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
