from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Any

from src.config import DATA_QUALITY_CONFIDENCE, VERSION_DEFAULTS

DIMENSION_SIGNALS = {
    "earnings_score": {
        "support": {"revenue_growth_up", "guidance_raise", "margin_expansion", "order_growth"},
        "negative": {"demand_slowdown", "guidance_cut", "margin_pressure", "inventory_build"},
        "risk_dimension": False,
    },
    "capital_score": {
        "support": {
            "institutional_inflow",
            "etf_inflow",
            "volume_breakout",
            "relative_strength_up",
        },
        "negative": {
            "institutional_outflow",
            "etf_outflow",
            "liquidity_drop",
            "relative_strength_down",
        },
        "risk_dimension": False,
    },
    "valuation_risk_score": {
        "support": {"valuation_extreme", "multiple_expansion_fast", "crowded_positioning"},
        "negative": {"valuation_reset", "earnings_catchup"},
        "risk_dimension": True,
    },
    "momentum_score": {
        "support": {
            "news_frequency_up",
            "research_mentions_up",
            "management_mentions_up",
            "keyword_breakout",
        },
        "negative": {"language_decay", "coverage_drop"},
        "risk_dimension": False,
    },
    "counter_evidence_risk_score": {
        "support": {
            "demand_slowdown",
            "margin_pressure",
            "regulatory_risk",
            "order_cancel",
            "technology_substitution",
            "policy_tightening",
        },
        "negative": {"risk_resolved", "policy_support"},
        "risk_dimension": True,
    },
}


def calculate_dimension_score(
    dimension: str,
    signal_events: list[dict[str, Any]],
    as_of_date: str,
    data_quality: str = "mock",
) -> dict[str, Any]:
    config = DIMENSION_SIGNALS[dimension]
    support_values = [
        _decayed_strength(event, as_of_date)
        for event in signal_events
        if event["signal_type"] in config["support"]
    ]
    negative_values = [
        _decayed_strength(event, as_of_date)
        for event in signal_events
        if event["signal_type"] in config["negative"]
    ]

    supporting_signal_count = len(support_values)
    risk_signal_count = len(negative_values)
    if not support_values and not negative_values:
        return {
            "score": 50,
            "confidence": 0,
            "data_quality": "unavailable",
            "supporting_signal_count": 0,
            "risk_signal_count": 0,
        }

    support_pressure = mean(support_values) if support_values else 0
    negative_pressure = mean(negative_values) if negative_values else 0

    if config["risk_dimension"]:
        score = 50 + 50 * support_pressure - 25 * negative_pressure
    else:
        score = 50 + 50 * support_pressure - 50 * negative_pressure

    confidences = [
        float(event.get("confidence", 0))
        * float(event.get("confidence_multiplier", 1))
        for event in signal_events
        if event["signal_type"] in config["support"] or event["signal_type"] in config["negative"]
    ]
    signal_confidence = mean(confidences) if confidences else 0
    data_quality_confidence = DATA_QUALITY_CONFIDENCE.get(data_quality, 0.5)

    return {
        "score": _clamp_score(score),
        "confidence": round(signal_confidence * data_quality_confidence, 4),
        "data_quality": data_quality,
        "supporting_signal_count": supporting_signal_count,
        "risk_signal_count": risk_signal_count,
    }


def score_narrative_state(
    narrative_id: str,
    signal_events: list[dict[str, Any]],
    mapping_confidence: float,
    evidence_count: int,
    as_of_date: str,
    data_quality: str = "mock",
) -> dict[str, Any]:
    narrative_events = [
        event for event in signal_events if event.get("narrative_id") == narrative_id
    ]
    dimensions = {
        dimension: calculate_dimension_score(
            dimension=dimension,
            signal_events=narrative_events,
            as_of_date=as_of_date,
            data_quality=data_quality,
        )
        for dimension in DIMENSION_SIGNALS
    }

    earnings_score = dimensions["earnings_score"]["score"]
    capital_score = dimensions["capital_score"]["score"]
    momentum_score = dimensions["momentum_score"]["score"]
    valuation_risk_score = dimensions["valuation_risk_score"]["score"]
    counter_evidence_risk_score = dimensions["counter_evidence_risk_score"]["score"]

    sustainability_score = round(
        0.25 * earnings_score
        + 0.20 * capital_score
        + 0.20 * momentum_score
        + 0.15 * (100 - valuation_risk_score)
        + 0.20 * (100 - counter_evidence_risk_score),
        2,
    )
    confidence = _narrative_confidence(
        mapping_confidence=mapping_confidence,
        dimensions=dimensions,
        evidence_count=evidence_count,
        signal_events=narrative_events,
        as_of_date=as_of_date,
        data_quality=data_quality,
    )

    return {
        "narrative_id": narrative_id,
        "dimensions": dimensions,
        "sustainability_score": sustainability_score,
        "stage": _select_stage(
            sustainability_score=sustainability_score,
            earnings_score=earnings_score,
            capital_score=capital_score,
            momentum_score=momentum_score,
            valuation_risk_score=valuation_risk_score,
            counter_evidence_risk_score=counter_evidence_risk_score,
            has_positive_fresh_evidence=_has_positive_fresh_evidence(
                narrative_events, as_of_date
            ),
        ),
        "confidence": confidence,
        "evidence_density": _evidence_density(evidence_count),
        "counter_signal_risk": _risk_label(counter_evidence_risk_score),
        "data_quality": data_quality,
        "previous_state": None,
        "state_change": None,
        "state_change_reason": None,
        "scoring_model_version": VERSION_DEFAULTS["scoring_model_version"],
    }


def _decayed_strength(event: dict[str, Any], as_of_date: str) -> float:
    as_of = date.fromisoformat(as_of_date)
    event_date = date.fromisoformat(event["event_date"])
    age_days = max((as_of - event_date).days, 0)
    half_life_days = float(event.get("half_life_days") or 45)
    confidence_multiplier = float(event.get("confidence_multiplier", 1))
    return (
        float(event["strength"])
        * float(event.get("confidence", 1))
        * confidence_multiplier
        * (0.5 ** (age_days / half_life_days))
    )


def _clamp_score(value: float) -> int:
    return max(0, min(100, round(value)))


def _narrative_confidence(
    mapping_confidence: float,
    dimensions: dict[str, dict[str, Any]],
    evidence_count: int,
    signal_events: list[dict[str, Any]],
    as_of_date: str,
    data_quality: str,
) -> float:
    dimension_confidences = [
        dimension["confidence"]
        for dimension in dimensions.values()
        if dimension["confidence"] > 0
    ]
    signal_confidence = mean(dimension_confidences) if dimension_confidences else 0
    evidence_density_confidence = min(evidence_count / 5, 1)
    freshness_confidence = _freshness_confidence(signal_events, as_of_date)
    data_quality_confidence = DATA_QUALITY_CONFIDENCE.get(data_quality, 0.5)

    return round(
        mean(
            [
                float(mapping_confidence),
                signal_confidence,
                evidence_density_confidence,
                freshness_confidence,
                data_quality_confidence,
            ]
        ),
        4,
    )


def _freshness_confidence(signal_events: list[dict[str, Any]], as_of_date: str) -> float:
    if not signal_events:
        return 0
    as_of = date.fromisoformat(as_of_date)
    newest_age = min(
        max((as_of - date.fromisoformat(event["event_date"])).days, 0)
        for event in signal_events
    )
    if newest_age <= 14:
        return 1
    if newest_age <= 45:
        return 0.75
    if newest_age <= 90:
        return 0.5
    return 0.25


def _has_positive_fresh_evidence(
    signal_events: list[dict[str, Any]], as_of_date: str
) -> bool:
    as_of = date.fromisoformat(as_of_date)
    for event in signal_events:
        if event["signal_type"] not in {
            "guidance_raise",
            "revenue_growth_up",
            "institutional_inflow",
            "etf_inflow",
            "research_mentions_up",
            "management_mentions_up",
            "keyword_breakout",
        }:
            continue
        age_days = max((as_of - date.fromisoformat(event["event_date"])).days, 0)
        if age_days <= 90 and float(event.get("strength", 0)) > 0.2:
            return True
    return False


def _select_stage(
    sustainability_score: float,
    earnings_score: int,
    capital_score: int,
    momentum_score: int,
    valuation_risk_score: int,
    counter_evidence_risk_score: int,
    has_positive_fresh_evidence: bool,
) -> str:
    if (
        sustainability_score < 35
        and momentum_score < 35
        and not has_positive_fresh_evidence
    ):
        return "dead"
    if sustainability_score < 45 and earnings_score < 45:
        return "weakening"
    if sustainability_score < 50 and counter_evidence_risk_score >= 60:
        return "weakening"
    if sustainability_score < 50 and momentum_score < 50:
        return "weakening"
    if counter_evidence_risk_score >= 70:
        return "weakening"
    if counter_evidence_risk_score >= 60:
        return "diverging"
    if earnings_score < 50 and (capital_score >= 60 or momentum_score >= 60):
        return "diverging"
    if valuation_risk_score >= 75 and (
        capital_score >= 65 or momentum_score >= 65
    ):
        return "crowded"
    if (
        sustainability_score >= 70
        and earnings_score >= 60
        and capital_score >= 60
        and counter_evidence_risk_score < 60
    ):
        return "expanding"
    if (
        sustainability_score >= 55
        and earnings_score >= 65
        and momentum_score >= 60
        and counter_evidence_risk_score < 60
        and valuation_risk_score < 75
    ):
        return "strengthening"
    if (
        sustainability_score >= 60
        and momentum_score >= 60
        and counter_evidence_risk_score < 60
        and valuation_risk_score < 75
    ):
        return "strengthening"
    if (
        momentum_score >= 60
        and earnings_score < 60
        and counter_evidence_risk_score < 60
    ):
        return "emerging"
    return "diverging"


def _evidence_density(evidence_count: int) -> str:
    if evidence_count >= 5:
        return "high"
    if evidence_count >= 2:
        return "medium"
    if evidence_count == 1:
        return "low"
    return "none"


def _risk_label(counter_evidence_risk_score: int) -> str:
    if counter_evidence_risk_score >= 70:
        return "high"
    if counter_evidence_risk_score >= 60:
        return "rising"
    if counter_evidence_risk_score >= 45:
        return "watch"
    return "low"
