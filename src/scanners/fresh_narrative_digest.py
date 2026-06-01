from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from html import escape
from typing import Any

SUPPORTED_STATES = ["new", "accelerating", "persistent", "cooling", "disputed"]
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
) -> dict[str, Any]:
    deduped_events = _dedupe_events(source_events)
    groups = _group_events_by_narrative(deduped_events)
    items = [
        _digest_item(
            narrative_key=narrative_key,
            events=events,
            window_start=window_start,
            window_end=window_end,
        )
        for narrative_key, events in sorted(groups.items())
    ]
    return {
        "version": "fresh-narrative-digest-v1",
        "generated_at": generated_at or _utc_now(),
        "status": "ok",
        "fixture_mode": fixture_mode,
        "window": {
            "start": window_start,
            "end": window_end,
        },
        "summary": {
            "raw_event_count": len(source_events),
            "deduped_event_count": len(deduped_events),
            "digest_item_count": len(items),
            "degraded_item_count": sum(1 for item in items if item["candidate_state"] == "disputed"),
        },
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
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def extract_source_events_from_probe(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in _list(payload.get("source_results")):
        rows.extend(row for row in _list(_mapping(result).get("rows")) if isinstance(row, dict))
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
    labels = _unique(str(_mapping(event.get("source_quality")).get("label") or _trust_tier(event)) for event in events)
    return {
        "best_trust_tier": best,
        "source_quality_labels": labels,
        "license_scopes": _unique(str(event.get("license_scope") or "") for event in events if event.get("license_scope")),
        "retention_policies": _unique(str(event.get("retention_policy") or "") for event in events if event.get("retention_policy")),
    }


def _trust_tier(event: dict[str, Any]) -> str:
    return str(event.get("source_trust_tier") or _mapping(event.get("meta")).get("trust_tier") or "candidate_untrusted")


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
