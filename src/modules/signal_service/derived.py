from __future__ import annotations

from typing import Any

ANNOUNCEMENT_DERIVED_SIGNAL_PROVIDER = "cninfo-derived-signals"

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
    signals = [
        _to_signal_event(item)
        for item in evidence_items
        if _to_signal_event(item) is not None
    ]
    return sorted(
        signals,
        key=lambda item: (
            item["narrative_id"],
            item["event_date"],
            item["signal_id"],
        ),
    )


def _to_signal_event(item: dict[str, Any]) -> dict[str, Any] | None:
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


def _confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    return round(max(0, min(1, numeric)), 3)
