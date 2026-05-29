from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
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
            "/api/v1/narratives/radar/scores",
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


def radar_scores(
    *,
    events: list[dict[str, Any]],
    config: ServiceConfig,
    as_of: str = "",
    window_days: Any = "",
    baseline_days: Any = "",
    half_life_hours: Any = "",
) -> dict[str, Any]:
    scoring_config = _scoring_config(
        as_of=as_of,
        window_days=window_days,
        baseline_days=baseline_days,
        half_life_hours=half_life_hours,
    )
    signals = radar_source_signals(events)["signals"]
    adapter = LocalMarketConfirmationAdapter(config.market_confirmation_path)
    confirmations = adapter.confirmations_by_candidate()
    scores = [
        _score_candidate(
            candidate_id=candidate_id,
            rows=rows,
            scoring_config=scoring_config,
            market_confirmation=confirmations.get(candidate_id, {}),
        )
        for candidate_id, rows in _signals_by_candidate(signals).items()
    ]
    warnings = [
        warning
        for score in scores
        for warning in _list(score.get("degradation_warnings"))
    ]
    return {
        "version": "narrative-radar-scores-v1",
        "scoring_config": {
            "as_of": scoring_config["as_of"].isoformat(),
            "window_days": scoring_config["window_days"],
            "baseline_days": scoring_config["baseline_days"],
            "recency_decay_half_life_hours": scoring_config["half_life_hours"],
            "formula_version": RADAR_FORMULA_VERSION,
        },
        "market_confirmation_adapter": adapter.metadata(),
        "scores": sorted(
            scores,
            key=lambda item: (
                -_float(item.get("heat_score")),
                str(item.get("candidate_narrative_id") or ""),
            ),
        ),
        "degradation_warnings": warnings,
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


class LocalMarketConfirmationAdapter:
    def __init__(self, path: Path):
        self.path = path

    def metadata(self) -> dict[str, Any]:
        return {
            "adapter": "local_contract_fixture",
            "source_owner": "gateway",
            "direct_provider_access": False,
            "path": str(self.path),
        }

    def confirmations_by_candidate(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            str(item.get("candidate_narrative_id") or ""): dict(item)
            for item in _list(payload.get("items"))
            if item.get("candidate_narrative_id")
        }


def _scoring_config(
    *,
    as_of: str,
    window_days: Any,
    baseline_days: Any,
    half_life_hours: Any,
) -> dict[str, Any]:
    return {
        "as_of": _parse_datetime(as_of) if as_of else datetime.now(UTC),
        "window_days": max(1, int(_float(window_days, default=1))),
        "baseline_days": max(2, int(_float(baseline_days, default=7))),
        "half_life_hours": max(1.0, _float(half_life_hours, default=24.0)),
    }


def _signals_by_candidate(
    signals: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for signal in signals:
        candidate_id = str(signal.get("candidate_narrative_id") or "")
        if not candidate_id:
            continue
        grouped[candidate_id] = [*grouped.get(candidate_id, []), signal]
    return grouped


def _score_candidate(
    *,
    candidate_id: str,
    rows: list[dict[str, Any]],
    scoring_config: dict[str, Any],
    market_confirmation: dict[str, Any],
) -> dict[str, Any]:
    as_of = scoring_config["as_of"]
    window_days = int(scoring_config["window_days"])
    baseline_days = int(scoring_config["baseline_days"])
    half_life_hours = float(scoring_config["half_life_hours"])
    window_start_dt = as_of - timedelta(days=window_days)
    baseline_start_dt = as_of - timedelta(days=baseline_days)
    current_rows = _rows_between(rows, start=window_start_dt, end=as_of)
    baseline_rows = _rows_between(rows, start=baseline_start_dt, end=window_start_dt)
    previous_rows = _rows_between(
        rows,
        start=window_start_dt - timedelta(days=window_days),
        end=window_start_dt,
    )
    current_attention = _attention(
        current_rows,
        window_start=window_start_dt,
        half_life_hours=half_life_hours,
    )
    baseline_attention = _attention(
        baseline_rows,
        window_start=window_start_dt,
        half_life_hours=half_life_hours,
    )
    previous_attention = _attention(
        previous_rows,
        window_start=window_start_dt,
        half_life_hours=half_life_hours,
    )
    baseline_day_count = max(1, baseline_days - window_days)
    baseline_daily_average = baseline_attention / baseline_day_count
    market_score, market_warnings = _market_confirmation_score(
        candidate_id=candidate_id,
        confirmation=market_confirmation,
    )
    score_warnings = [
        *_degradation_warnings(rows),
        *market_warnings,
    ]
    return {
        "candidate_narrative_id": candidate_id,
        "narrative_name": _narrative_name(rows, candidate_id),
        "heat_score": round(min(100.0, current_attention * 50.0), 2),
        "trend_score": round(
            max(0.0, min(100.0, 50.0 + (current_attention - baseline_daily_average) * 20.0)),
            2,
        ),
        "trend_acceleration": round((current_attention - previous_attention) * 20.0, 2),
        "momentum_state": _momentum_state(
            current_attention=current_attention,
            previous_attention=previous_attention,
            baseline_daily_average=baseline_daily_average,
        ),
        "market_confirmation_score": market_score,
        "evidence_quality_score": _evidence_quality_score(rows),
        "source_attention_components": {
            "current_weighted_attention": round(current_attention, 2),
            "baseline_weighted_attention": round(baseline_attention, 2),
            "baseline_daily_average": round(baseline_daily_average, 2),
            "previous_window_weighted_attention": round(previous_attention, 2),
            "source_signal_count": len(rows),
            "current_source_signal_count": len(current_rows),
        },
        "window_start": window_start_dt.isoformat(),
        "window_end": as_of.isoformat(),
        "baseline_window": {
            "window_start": baseline_start_dt.isoformat(),
            "window_end": window_start_dt.isoformat(),
            "average_weighted_attention": round(baseline_daily_average, 2),
        },
        "formula_version": RADAR_FORMULA_VERSION,
        "degradation_warnings": score_warnings,
    }


def _rows_between(
    rows: list[dict[str, Any]],
    *,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if start <= _parse_datetime(str(row.get("event_time") or "")) < end
    ]


def _attention(
    rows: list[dict[str, Any]],
    *,
    window_start: datetime,
    half_life_hours: float,
) -> float:
    return sum(
        _float(row.get("weighted_attention"))
        * _recency_decay(
            event_time=_parse_datetime(str(row.get("event_time") or "")),
            window_start=window_start,
            half_life_hours=half_life_hours,
        )
        for row in rows
    )


def _recency_decay(
    *,
    event_time: datetime,
    window_start: datetime,
    half_life_hours: float,
) -> float:
    if event_time >= window_start:
        return 1.0
    half_life_days = max(1.0 / 24.0, half_life_hours / 24.0)
    days_back = max(0, (window_start.date() - event_time.date()).days)
    return 0.5 ** (days_back / half_life_days)


def _market_confirmation_score(
    *,
    candidate_id: str,
    confirmation: dict[str, Any],
) -> tuple[float, list[dict[str, str]]]:
    if not confirmation:
        return 0.0, [
            {
                "code": "MARKET_CONFIRMATION_MISSING",
                "message": (
                    f"No normalized market confirmation is available for {candidate_id}."
                ),
                "classification": "source_degraded",
            }
        ]
    status = str(confirmation.get("status") or "available")
    score = round(_float(confirmation.get("market_confirmation_score")), 2)
    if status == "available":
        return score, []
    return score, [
        {
            "code": "MARKET_CONFIRMATION_DEGRADED",
            "message": (
                f"Market confirmation for {candidate_id} is {status}; source heat "
                "is retained."
            ),
            "classification": "source_degraded",
        }
    ]


def _evidence_quality_score(rows: list[dict[str, Any]]) -> float:
    source_types = {str(row.get("source_type") or "") for row in rows}
    rows_with_refs = [row for row in rows if _strings(row.get("evidence_refs"))]
    reference_ratio = len(rows_with_refs) / len(rows) if rows else 0.0
    score = 40.0 + min(2, len(source_types)) * 20.0 + reference_ratio * 20.0
    return round(min(100.0, score), 2)


def _momentum_state(
    *,
    current_attention: float,
    previous_attention: float,
    baseline_daily_average: float,
) -> str:
    if current_attention >= previous_attention > baseline_daily_average:
        return "heating"
    if current_attention > baseline_daily_average and previous_attention == 0:
        return "emerging"
    if current_attention < previous_attention:
        return "cooling"
    return "stable"


def _narrative_name(rows: list[dict[str, Any]], candidate_id: str) -> str:
    for row in rows:
        name = str(row.get("narrative_name") or "").strip()
        if name:
            return name
    return candidate_id


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
    if " " in cleaned and cleaned.rsplit(" ", 1)[-1].count(":") == 1:
        prefix, offset = cleaned.rsplit(" ", 1)
        cleaned = f"{prefix}+{offset}"
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
