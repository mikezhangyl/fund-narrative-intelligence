from __future__ import annotations

from typing import Any

from src.modules.signal_service.scoring import DIMENSION_SIGNALS

SIGNAL_TRACE_VERSION = "signal-trace-v1"

_SOURCE_LAYER_BY_SIGNAL_SOURCE = {
    "cninfo_announcement": "announcements",
    "market_quote": "market_quotes",
    "news_evidence": "news_evidence",
    "valuation_snapshot": "valuation",
}


def build_signal_trace_payload(
    *,
    fund_code: str,
    as_of_date: str,
    provider_foundation: dict[str, Any],
    narratives: list[dict[str, Any]],
    signal_events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "version": SIGNAL_TRACE_VERSION,
        "fund_code": fund_code,
        "as_of_date": as_of_date,
        "provider_foundation": provider_foundation,
        "signal_count": len(signal_events),
        "narratives": [
            _narrative_trace(
                narrative=narrative,
                signal_events=[
                    event
                    for event in signal_events
                    if event.get("narrative_id") == narrative.get("narrative_id")
                ],
                provider_foundation=provider_foundation,
            )
            for narrative in narratives
        ],
    }


def _narrative_trace(
    *,
    narrative: dict[str, Any],
    signal_events: list[dict[str, Any]],
    provider_foundation: dict[str, Any],
) -> dict[str, Any]:
    state = narrative.get("state", {})
    return {
        "narrative_id": str(narrative.get("narrative_id") or ""),
        "name": str(narrative.get("name") or ""),
        "stage": str(state.get("stage") or ""),
        "sustainability_score": state.get("sustainability_score"),
        "confidence": state.get("confidence"),
        "dimensions": [
            _dimension_trace(
                dimension=dimension,
                dimension_state=state["dimensions"][dimension],
                signal_events=signal_events,
                provider_foundation=provider_foundation,
            )
            for dimension in DIMENSION_SIGNALS
        ],
    }


def _dimension_trace(
    *,
    dimension: str,
    dimension_state: dict[str, Any],
    signal_events: list[dict[str, Any]],
    provider_foundation: dict[str, Any],
) -> dict[str, Any]:
    signal_config = DIMENSION_SIGNALS[dimension]
    dimension_signals = [
        _signal_trace(
            signal_event=event,
            role=_signal_role(event["signal_type"], signal_config),
            provider_foundation=provider_foundation,
        )
        for event in signal_events
        if event["signal_type"] in signal_config["support"]
        or event["signal_type"] in signal_config["negative"]
    ]
    return {
        "dimension": dimension,
        "score": dimension_state["score"],
        "confidence": dimension_state["confidence"],
        "data_quality": dimension_state["data_quality"],
        "supporting_signal_count": dimension_state["supporting_signal_count"],
        "risk_signal_count": dimension_state["risk_signal_count"],
        "signals": sorted(
            dimension_signals,
            key=lambda item: (
                item["event_date"],
                item["signal_id"],
            ),
        ),
    }


def _signal_role(signal_type: str, signal_config: dict[str, Any]) -> str:
    if signal_type in signal_config["support"]:
        return "support"
    return "negative"


def _signal_trace(
    *,
    signal_event: dict[str, Any],
    role: str,
    provider_foundation: dict[str, Any],
) -> dict[str, Any]:
    layer_name = _source_layer_name(signal_event, provider_foundation)
    layer = provider_foundation["layers"][layer_name]
    return {
        "signal_id": str(signal_event.get("signal_id") or ""),
        "signal_type": str(signal_event.get("signal_type") or ""),
        "role": role,
        "strength": signal_event.get("strength"),
        "confidence": signal_event.get("confidence"),
        "confidence_multiplier": signal_event.get("confidence_multiplier"),
        "event_date": str(signal_event.get("event_date") or ""),
        "half_life_days": signal_event.get("half_life_days"),
        "source": str(signal_event.get("source") or "signal_event"),
        "source_provider": str(signal_event.get("source_provider") or layer["provider_name"]),
        "source_url": str(signal_event.get("source_url") or layer["source_url"]),
        "source_stock_code": signal_event.get("source_stock_code"),
        "source_layer": layer_name,
        "source_layer_is_mock": layer["is_mock"],
    }


def _source_layer_name(
    signal_event: dict[str, Any],
    provider_foundation: dict[str, Any],
) -> str:
    layers = provider_foundation["layers"]
    source = str(signal_event.get("source") or "")
    preferred_layer = _SOURCE_LAYER_BY_SIGNAL_SOURCE.get(source, "signals")
    if preferred_layer in layers:
        return preferred_layer
    if source and "derived_signals" in layers:
        return "derived_signals"
    return "signals"
