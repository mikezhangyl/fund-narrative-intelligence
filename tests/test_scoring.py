from src.modules.signal_service.scoring import (
    calculate_dimension_score,
    score_narrative_state,
)


def test_support_dimension_uses_decayed_signal_pressure():
    events = [
        {
            "signal_id": "SIG_POS",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "guidance_raise",
            "strength": 0.8,
            "confidence": 1.0,
            "confidence_multiplier": 1.0,
            "event_date": "2026-05-13",
            "half_life_days": 45,
        },
        {
            "signal_id": "SIG_NEG",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "margin_pressure",
            "strength": 0.2,
            "confidence": 1.0,
            "confidence_multiplier": 1.0,
            "event_date": "2026-05-13",
            "half_life_days": 45,
        },
    ]

    result = calculate_dimension_score(
        dimension="earnings_score",
        signal_events=events,
        as_of_date="2026-05-13",
    )

    assert result["score"] == 80
    assert result["confidence"] > 0
    assert result["data_quality"] == "mock"


def test_missing_dimension_data_returns_neutral_score_with_zero_confidence():
    result = calculate_dimension_score(
        dimension="capital_score",
        signal_events=[],
        as_of_date="2026-05-13",
    )

    assert result == {
        "score": 50,
        "confidence": 0,
        "data_quality": "unavailable",
        "supporting_signal_count": 0,
        "risk_signal_count": 0,
    }


def test_narrative_state_scores_dimensions_and_stage():
    signal_events = [
        {
            "signal_id": "SIG_EARNINGS",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "guidance_raise",
            "strength": 0.8,
            "confidence": 0.9,
            "confidence_multiplier": 1.0,
            "event_date": "2026-05-13",
            "half_life_days": 45,
        },
        {
            "signal_id": "SIG_CAPITAL",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "institutional_inflow",
            "strength": 0.7,
            "confidence": 0.9,
            "confidence_multiplier": 1.0,
            "event_date": "2026-05-13",
            "half_life_days": 30,
        },
        {
            "signal_id": "SIG_MOMENTUM",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "research_mentions_up",
            "strength": 0.75,
            "confidence": 0.9,
            "confidence_multiplier": 1.0,
            "event_date": "2026-05-13",
            "half_life_days": 30,
        },
        {
            "signal_id": "SIG_VALUATION",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "valuation_extreme",
            "strength": 0.2,
            "confidence": 0.8,
            "confidence_multiplier": 1.0,
            "event_date": "2026-05-13",
            "half_life_days": 60,
        },
    ]

    result = score_narrative_state(
        narrative_id="N_AI_INFRA",
        signal_events=signal_events,
        mapping_confidence=0.82,
        evidence_count=4,
        as_of_date="2026-05-13",
        data_quality="mock",
    )

    assert result["narrative_id"] == "N_AI_INFRA"
    assert result["dimensions"]["earnings_score"]["score"] >= 80
    assert result["dimensions"]["capital_score"]["score"] >= 75
    assert result["dimensions"]["momentum_score"]["score"] >= 75
    assert result["stage"] in {"strengthening", "expanding"}
    assert 0 <= result["confidence"] <= 1
    assert result["scoring_model_version"] == "scoring-v1"
