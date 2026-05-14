from __future__ import annotations

from typing import Any

ANNOUNCEMENT_DERIVED_SIGNAL_PROVIDER = "cninfo-derived-signals"
MARKET_QUOTE_DERIVED_SIGNAL_PROVIDER = "market-quote-derived-signals"
NEWS_DERIVED_SIGNAL_PROVIDER = "news-derived-signals"
VALUATION_DERIVED_SIGNAL_PROVIDER = "valuation-derived-signals"

_ANNOUNCEMENT_SIGNAL_MAP = {
    ("earnings", "positive"): (
        "revenue_growth_up",
        "positive earnings announcement evidence",
        45,
        1.0,
        0.85,
    ),
    ("orders", "positive"): (
        "order_growth",
        "positive order announcement evidence",
        45,
        1.0,
        0.85,
    ),
    ("capital_flow", "positive"): (
        "institutional_inflow",
        "positive capital-flow announcement evidence",
        30,
        1.0,
        0.85,
    ),
    ("risk", "negative"): (
        "regulatory_risk",
        "negative risk announcement evidence",
        60,
        1.0,
        0.85,
    ),
    ("financial_report", "mixed"): (
        "management_mentions_up",
        "mixed financial disclosure announcement evidence",
        30,
        0.6,
        0.55,
    ),
    ("governance", "mixed"): (
        "management_mentions_up",
        "mixed governance disclosure announcement evidence",
        30,
        0.5,
        0.55,
    ),
}


def derive_announcement_signal_events(
    evidence_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals = []
    for item in evidence_items:
        signal = _announcement_evidence_to_signal_event(item)
        if signal is not None:
            signals.append(signal)
    return sorted(
        signals,
        key=lambda item: (
            item["narrative_id"],
            item["event_date"],
            item["signal_id"],
        ),
    )


def derive_news_signal_events(
    evidence_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals = []
    for item in evidence_items:
        signal = _news_evidence_to_signal_event(item)
        if signal is not None:
            signals.append(signal)
    return sorted(
        signals,
        key=lambda item: (
            item["narrative_id"],
            item["event_date"],
            item["signal_id"],
        ),
    )


def derive_market_quote_signal_events(
    market_quotes_payload: dict[str, Any],
    stock_mappings: list[dict[str, Any]],
    as_of_date: str,
) -> list[dict[str, Any]]:
    quotes = market_quotes_payload.get("quotes")
    if not isinstance(quotes, list):
        return []
    mappings_by_stock = _mappings_by_stock(stock_mappings)
    signals = [
        signal
        for quote in quotes
        for signal in _quote_signals(
            quote=quote,
            stock_mappings=mappings_by_stock.get(str(quote.get("stock_code") or ""), []),
            data_quality=str(market_quotes_payload.get("data_quality") or "unavailable"),
            as_of_date=as_of_date,
        )
    ]
    return sorted(
        signals,
        key=lambda item: (
            item["narrative_id"],
            item["event_date"],
            item["signal_id"],
        ),
    )


def derive_valuation_signal_events(
    valuation_snapshots_payload: dict[str, Any],
    stock_mappings: list[dict[str, Any]],
    as_of_date: str,
) -> list[dict[str, Any]]:
    if valuation_snapshots_payload.get("valuation_basis") != "provider_valuation_metrics":
        return []
    valuations = valuation_snapshots_payload.get("valuations")
    if not isinstance(valuations, list):
        return []
    mappings_by_stock = _mappings_by_stock(stock_mappings)
    signals = [
        signal
        for valuation in valuations
        for signal in _valuation_signals(
            valuation=valuation,
            stock_mappings=mappings_by_stock.get(
                str(valuation.get("stock_code") or ""), []
            ),
            data_quality=str(valuation_snapshots_payload.get("data_quality") or "unavailable"),
            fallback_provider=str(valuation_snapshots_payload.get("provider_name") or ""),
            fallback_url=valuation_snapshots_payload.get("source_url"),
            as_of_date=as_of_date,
        )
    ]
    return sorted(
        signals,
        key=lambda item: (
            item["narrative_id"],
            item["event_date"],
            item["signal_id"],
        ),
    )


def _announcement_evidence_to_signal_event(item: dict[str, Any]) -> dict[str, Any] | None:
    if item.get("source") != "cninfo_announcement":
        return None
    profile = _ANNOUNCEMENT_SIGNAL_MAP.get(
        (str(item.get("type") or ""), str(item.get("sentiment") or ""))
    )
    if profile is None:
        return None

    evidence_id = str(item.get("evidence_id") or "")
    narrative_id = str(item.get("narrative_id") or "")
    event_date = str(item.get("event_date") or "")
    if not evidence_id or not narrative_id or not event_date:
        return None

    signal_type, reason, half_life_days, strength_multiplier, confidence_multiplier = profile
    confidence = _confidence(item.get("confidence"))
    strength = round(confidence * strength_multiplier, 3)
    return {
        "signal_id": f"SIG_ANN_{evidence_id}",
        "narrative_id": narrative_id,
        "signal_type": signal_type,
        "strength": strength,
        "confidence": confidence,
        "confidence_multiplier": confidence_multiplier,
        "event_date": event_date,
        "half_life_days": half_life_days,
        "source": "cninfo_announcement",
        "source_evidence_id": evidence_id,
        "source_url": item.get("source_url"),
        "derivation_reason": reason,
    }


def _news_evidence_to_signal_event(item: dict[str, Any]) -> dict[str, Any] | None:
    if item.get("type") != "news":
        return None
    evidence_id = str(item.get("evidence_id") or "")
    narrative_id = str(item.get("narrative_id") or "")
    event_date = str(item.get("event_date") or "")
    if not evidence_id or not narrative_id or not event_date:
        return None

    sentiment = str(item.get("sentiment") or "")
    if sentiment == "positive":
        signal_type = "news_frequency_up"
        strength_multiplier = 0.8
        confidence_multiplier = 0.55
    elif sentiment == "mixed":
        signal_type = "research_mentions_up"
        strength_multiplier = 0.5
        confidence_multiplier = 0.45
    elif sentiment == "negative":
        signal_type = "language_decay"
        strength_multiplier = 0.7
        confidence_multiplier = 0.55
    else:
        return None

    confidence = _confidence(item.get("confidence"))
    return {
        "signal_id": f"SIG_NEWS_{evidence_id}",
        "narrative_id": narrative_id,
        "signal_type": signal_type,
        "strength": round(confidence * strength_multiplier, 3),
        "confidence": confidence,
        "confidence_multiplier": confidence_multiplier,
        "event_date": event_date,
        "half_life_days": 14,
        "source": "news_evidence",
        "source_provider": str(item.get("source_provider") or ""),
        "source_evidence_id": evidence_id,
        "source_url": item.get("source_url"),
        "derivation_reason": "provider news evidence",
    }


def _quote_signals(
    quote: dict[str, Any],
    stock_mappings: list[dict[str, Any]],
    data_quality: str,
    as_of_date: str,
) -> list[dict[str, Any]]:
    change_percent = _optional_float(quote.get("change_percent"))
    if change_percent is None or abs(change_percent) < 1.5:
        return []
    signal_type = (
        "relative_strength_up" if change_percent > 0 else "relative_strength_down"
    )
    direction = "positive" if change_percent > 0 else "negative"
    stock_code = str(quote.get("stock_code") or "")
    source_provider = str(quote.get("source_provider") or "")
    source_url = quote.get("source_url")
    event_date = _quote_event_date(quote=quote, as_of_date=as_of_date)
    strength = round(min(abs(change_percent) / 5, 1), 3)
    data_quality_confidence = 0.8 if data_quality == "fresh" else 0.65
    suffix = "REL_STRENGTH_UP" if change_percent > 0 else "REL_STRENGTH_DOWN"
    return [
        {
            "signal_id": f"SIG_QUOTE_{stock_code}_{mapping['narrative_id']}_{suffix}",
            "narrative_id": str(mapping["narrative_id"]),
            "signal_type": signal_type,
            "strength": strength,
            "confidence": round(
                float(mapping.get("confidence", 0)) * data_quality_confidence * 0.6875,
                4,
            ),
            "confidence_multiplier": 0.65,
            "event_date": event_date,
            "half_life_days": 10,
            "source": "market_quote",
            "source_provider": source_provider,
            "source_stock_code": stock_code,
            "source_url": source_url,
            "derivation_reason": f"{direction} market quote change percent",
        }
        for mapping in stock_mappings
        if mapping.get("narrative_id")
    ]


def _valuation_signals(
    valuation: dict[str, Any],
    stock_mappings: list[dict[str, Any]],
    data_quality: str,
    fallback_provider: str,
    fallback_url: Any,
    as_of_date: str,
) -> list[dict[str, Any]]:
    profile = _valuation_signal_profile(valuation)
    if profile is None:
        return []
    signal_type, suffix, strength, reason = profile
    stock_code = str(valuation.get("stock_code") or "")
    source_provider = str(valuation.get("source_provider") or fallback_provider)
    source_url = valuation.get("source_url") or fallback_url
    event_date = _quote_event_date(quote=valuation, as_of_date=as_of_date)
    data_quality_confidence = _data_quality_confidence(data_quality)
    return [
        {
            "signal_id": f"SIG_VAL_{stock_code}_{mapping['narrative_id']}_{suffix}",
            "narrative_id": str(mapping["narrative_id"]),
            "signal_type": signal_type,
            "strength": strength,
            "confidence": round(float(mapping.get("confidence", 0)) * data_quality_confidence, 4),
            "confidence_multiplier": 0.75,
            "event_date": event_date,
            "half_life_days": 30,
            "source": "valuation_snapshot",
            "source_provider": source_provider,
            "source_stock_code": stock_code,
            "source_url": source_url,
            "derivation_reason": reason,
        }
        for mapping in stock_mappings
        if mapping.get("narrative_id")
    ]


def _valuation_signal_profile(
    valuation: dict[str, Any],
) -> tuple[str, str, float, str] | None:
    pressure = str(valuation.get("valuation_pressure") or "")
    if pressure == "elevated":
        return (
            "valuation_extreme",
            "VALUATION_EXTREME",
            _elevated_valuation_strength(valuation),
            "elevated provider valuation metrics",
        )
    if pressure == "discounted":
        return (
            "valuation_reset",
            "VALUATION_RESET",
            0.65,
            "discounted provider valuation metrics",
        )
    return None


def _elevated_valuation_strength(valuation: dict[str, Any]) -> float:
    pe_ttm = _optional_float(valuation.get("pe_ttm"))
    pb = _optional_float(valuation.get("pb"))
    if (pe_ttm is not None and pe_ttm >= 60) or (pb is not None and pb >= 12):
        return 1.0
    return 0.75


def _data_quality_confidence(data_quality: str) -> float:
    if data_quality == "fresh":
        return 0.75
    if data_quality == "partial":
        return 0.6
    return 0.4


def _confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    return round(max(0, min(1, numeric)), 3)


def _optional_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quote_event_date(quote: dict[str, Any], as_of_date: str) -> str:
    retrieved_at = str(quote.get("retrieved_at") or "")
    if len(retrieved_at) >= 10:
        return retrieved_at[:10]
    return as_of_date


def _mappings_by_stock(
    stock_mappings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    mappings_by_stock: dict[str, list[dict[str, Any]]] = {}
    for mapping in stock_mappings:
        stock_code = str(mapping.get("stock_code") or "")
        narrative_id = mapping.get("narrative_id")
        if not stock_code or not narrative_id:
            continue
        mappings_by_stock.setdefault(stock_code, []).append(mapping)
    return {
        stock_code: sorted(items, key=lambda item: str(item["narrative_id"]))
        for stock_code, items in mappings_by_stock.items()
    }
