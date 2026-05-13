from src.modules.report_writer.interpretation import interpret_narrative


def test_interpretation_explains_crowded_without_advice_language():
    narrative = {
        "name": "AI Power Demand",
        "state": {
            "stage": "crowded",
            "confidence": 0.62,
            "evidence_density": "medium",
            "counter_signal_risk": "watch",
            "data_quality": "mock",
            "sustainability_score": 55.45,
            "dimensions": {
                "valuation_risk_score": {"score": 84},
                "counter_evidence_risk_score": {"score": 48},
            },
        },
    }

    result = interpret_narrative(narrative)

    joined = " ".join(result.values()).lower()
    assert "crowded" in result["stage_explanation"].lower()
    assert "valuation" in result["risk_explanation"].lower()
    assert "mock" in result["confidence_note"].lower()
    assert "buy" not in joined
    assert "sell" not in joined
    assert "hold" not in joined


def test_interpretation_explains_dead_stage_as_thesis_failure():
    narrative = {
        "name": "EV Price War",
        "state": {
            "stage": "dead",
            "confidence": 0.7,
            "evidence_density": "medium",
            "counter_signal_risk": "high",
            "data_quality": "mock",
            "sustainability_score": 24.5,
            "dimensions": {
                "valuation_risk_score": {"score": 50},
                "counter_evidence_risk_score": {"score": 90},
            },
        },
    }

    result = interpret_narrative(narrative)

    assert "no longer has enough fresh support" in result["stage_explanation"]
    assert "counter-evidence" in result["risk_explanation"]
