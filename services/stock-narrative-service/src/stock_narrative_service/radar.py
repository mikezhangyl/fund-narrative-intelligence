from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from stock_narrative_service.config import ServiceConfig
from stock_narrative_service.identity import stable_id

RADAR_CONTRACT_VERSION = "narrative-radar-contract-v1"
RADAR_SIGNALS_VERSION = "narrative-radar-source-signals-v1"
RADAR_FORMULA_VERSION = "radar-deterministic-v0"

SOURCE_WEIGHT_BY_TYPE = {
    "announcement": 1.2,
    "news": 1.0,
    "manual": 0.8,
    "social_future": 0.0,
}


def radar_contract(config: ServiceConfig) -> dict[str, Any]:
    return {
        "version": RADAR_CONTRACT_VERSION,
        "ownership": {
            "radar_owner": "narrative_service",
            "provider_owner": "gateway",
            "consumer_role": "fni_consumes_service_api_only",
            "score_authority": "narrative_service",
        },
        "service_owned_endpoints": [
            "/api/v1/narratives/radar/contract",
            "/api/v1/narratives/radar/signals",
            "/api/v1/narratives/radar/bubbles",
            "/api/v1/narratives/radar/evidence",
        ],
        "response_envelope": {
            "status": "available|degraded|missing|failed",
            "source": "narrative_service",
            "provider": config.provider_name,
            "provider_version": config.provider_version,
            "data": "endpoint payload",
            "warnings": "degraded or missing source metadata",
            "diagnostics": "operational diagnostics",
            "trust_metadata": "candidate/trusted state metadata",
        },
        "score_schema": {
            "formula_version": RADAR_FORMULA_VERSION,
            "required_fields": [
                "heat_score",
                "trend_score",
                "momentum_state",
                "market_confirmation_score",
                "evidence_quality_score",
                "source_attention_components",
                "window_start",
                "window_end",
                "baseline_window",
                "formula_version",
                "degradation_warnings",
            ],
            "component_breakdown": {
                "heat_score": "weighted current attention over the active window",
                "trend_score": "active-window heat compared with baseline heat",
                "momentum_state": "emerging|heating|stable|cooling",
                "market_confirmation_score": (
                    "optional gateway/FNI market confirmation, never source text"
                ),
                "evidence_quality_score": "source mix, review state, and citation quality",
            },
            "ai_policy": (
                "AI summaries may explain evidence later but cannot override "
                "deterministic scores."
            ),
        },
        "time_series_model": radar_source_model(),
        "degraded_metadata_fields": [
            "degradation_warnings",
            "source_availability",
            "missing_source_types",
            "formula_version",
        ],
    }


def radar_source_signals(events: list[dict[str, Any]]) -> dict[str, Any]:
    signals = sorted(
        [
            signal
            for event in events
            for signal in _signals_from_event(event)
        ],
        key=lambda item: (
            str(item.get("event_time") or ""),
            str(item.get("source_event_id") or ""),
            str(item.get("candidate_narrative_id") or ""),
        ),
    )
    degradation_warnings = []
    if not signals:
        degradation_warnings.append(
            {
                "code": "RADAR_SOURCE_SIGNALS_EMPTY",
                "message": "No replayable radar source signals are available.",
                "classification": "product_data_gap",
            }
        )
    return {
        "version": RADAR_SIGNALS_VERSION,
        "source_model": radar_source_model(),
        "signals": signals,
        "window_snapshots": _daily_snapshots(signals),
        "degradation_warnings": degradation_warnings,
        "source_availability": _source_availability(signals),
        "missing_source_types": _missing_source_types(signals),
    }


def radar_source_model() -> dict[str, Any]:
    return {
        "storage_model": "append_only_source_signal_ledger",
        "window_granularities": ["hourly", "daily"],
        "signal_fields": [
            "signal_id",
            "source_event_id",
            "source_type",
            "candidate_narrative_id",
            "extracted_entities",
            "event_time",
            "ingested_at",
            "signal_strength",
            "source_weight",
            "evidence_refs",
            "source_metadata",
        ],
        "snapshot_fields": [
            "window_id",
            "granularity",
            "window_start",
            "window_end",
            "candidate_narrative_id",
            "source_signal_count",
            "weighted_attention",
            "source_event_ids",
            "degradation_warnings",
        ],
        "storage_migration": (
            "Local JSON replay and durable database adapters must preserve this "
            "public API shape."
        ),
        "negative_cache_policy": "failed upstream/provider attempts are not cached",
    }


def _signals_from_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    event_id = str(event.get("event_id") or "").strip()
    source_type = str(event.get("source_type") or "manual").strip() or "manual"
    event_time = str(event.get("event_time") or "").strip()
    ingested_at = str(event.get("ingested_at") or event.get("recorded_at") or event_time)
    source_weight = _float(
        event.get("source_weight"),
        default=SOURCE_WEIGHT_BY_TYPE.get(source_type, 0.5),
    )
    source_metadata = _mapping(event.get("source_metadata"))
    extracted_entities = _extracted_entities(event)
    return [
        _signal(
            event_id=event_id,
            source_type=source_type,
            event_time=event_time,
            ingested_at=ingested_at,
            source_weight=source_weight,
            source_metadata=source_metadata,
            extracted_entities=extracted_entities,
            candidate=candidate,
        )
        for candidate in _list(event.get("candidate_narratives"))
    ]


def _signal(
    *,
    event_id: str,
    source_type: str,
    event_time: str,
    ingested_at: str,
    source_weight: float,
    source_metadata: dict[str, Any],
    extracted_entities: dict[str, list[str]],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(
        candidate.get("candidate_narrative_id")
        or candidate.get("narrative_id")
        or ""
    ).strip()
    signal_strength = _float(candidate.get("confidence"), default=0.5)
    return {
        "signal_id": stable_id("RSIG", [event_id, candidate_id]),
        "source_event_id": event_id,
        "source_type": source_type,
        "candidate_narrative_id": candidate_id,
        "narrative_name": str(
            candidate.get("name") or candidate.get("narrative_name") or candidate_id
        ),
        "extracted_entities": extracted_entities,
        "event_time": event_time,
        "ingested_at": ingested_at,
        "signal_strength": round(signal_strength, 4),
        "source_weight": round(source_weight, 4),
        "weighted_attention": round(signal_strength * source_weight, 4),
        "evidence_refs": _evidence_refs(candidate),
        "source_metadata": source_metadata,
        "trust_status": str(candidate.get("trust_status") or "candidate_untrusted"),
    }


def _daily_snapshots(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for signal in signals:
        window_start = _day_start(str(signal.get("event_time") or ""))
        key = (window_start, str(signal.get("candidate_narrative_id") or ""))
        grouped[key] = [*grouped.get(key, []), signal]
    snapshots = [
        _daily_snapshot(window_start=window_start, candidate_id=candidate_id, rows=rows)
        for (window_start, candidate_id), rows in grouped.items()
    ]
    return sorted(
        snapshots,
        key=lambda item: (
            str(item.get("window_start") or ""),
            str(item.get("candidate_narrative_id") or ""),
        ),
    )


def _daily_snapshot(
    *,
    window_start: str,
    candidate_id: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    weighted_attention = round(
        sum(_float(row.get("weighted_attention")) for row in rows),
        2,
    )
    total_signal_strength = round(
        sum(_float(row.get("signal_strength")) for row in rows),
        2,
    )
    source_event_ids = sorted({str(row.get("source_event_id") or "") for row in rows})
    source_types = sorted({str(row.get("source_type") or "") for row in rows})
    narrative_name = str(rows[0].get("narrative_name") or candidate_id) if rows else candidate_id
    return {
        "window_id": f"daily:{window_start[:10]}:{candidate_id}",
        "granularity": "daily",
        "window_start": window_start,
        "window_end": _window_end(window_start, days=1),
        "candidate_narrative_id": candidate_id,
        "narrative_name": narrative_name,
        "source_signal_count": len(rows),
        "source_count": len(source_types),
        "total_signal_strength": total_signal_strength,
        "weighted_attention": weighted_attention,
        "source_event_ids": source_event_ids,
        "source_types": source_types,
        "degradation_warnings": _degradation_warnings(rows),
    }


def _source_availability(signals: list[dict[str, Any]]) -> dict[str, str]:
    available = {str(signal.get("source_type") or "") for signal in signals}
    return {
        source_type: ("available" if source_type in available else "missing")
        for source_type in ("news", "announcement", "manual")
    }


def _missing_source_types(signals: list[dict[str, Any]]) -> list[str]:
    availability = _source_availability(signals)
    return [source_type for source_type, status in availability.items() if status == "missing"]


def _degradation_warnings(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    warnings = []
    for row in rows:
        state = str(
            _mapping(row.get("source_metadata")).get("degradation_state") or "available"
        )
        if state in {"available", ""}:
            continue
        warnings.append(
            {
                "code": f"SOURCE_{state.upper()}",
                "source_event_id": str(row.get("source_event_id") or ""),
                "source_type": str(row.get("source_type") or ""),
                "classification": "source_degraded",
            }
        )
    return warnings


def _extracted_entities(event: dict[str, Any]) -> dict[str, list[str]]:
    extracted = _mapping(event.get("extracted_entities"))
    return {
        "tickers": _strings(extracted.get("tickers") or event.get("stock_codes")),
        "sectors": _strings(extracted.get("sectors") or event.get("sectors")),
        "concepts": _strings(extracted.get("concepts") or event.get("concepts")),
        "keywords": _strings(
            extracted.get("keywords")
            or event.get("keywords")
            or event.get("narrative_hints")
        ),
    }


def _evidence_refs(candidate: dict[str, Any]) -> list[str]:
    return (
        _strings(candidate.get("representative_citation_ids"))
        or _strings(candidate.get("evidence_refs"))
        or _strings(candidate.get("source_event_ids"))
    )


def _day_start(value: str) -> str:
    parsed = _parse_datetime(value)
    return parsed.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _window_end(window_start: str, *, days: int) -> str:
    return (_parse_datetime(window_start) + timedelta(days=days)).isoformat()


def _parse_datetime(value: str) -> datetime:
    cleaned = str(value or "").strip()
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    if not cleaned:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
