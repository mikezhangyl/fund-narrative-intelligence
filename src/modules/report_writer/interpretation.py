from __future__ import annotations

from typing import Any

STAGE_EXPLANATIONS = {
    "emerging": "This narrative is early: market language is improving, but earnings or capital validation is still incomplete.",
    "strengthening": "This narrative is strengthening: supporting signals are still visible and counter-evidence is not yet dominant.",
    "expanding": "This narrative is expanding: earnings, capital, and momentum signals are aligned in the current evidence set.",
    "crowded": "This narrative is crowded: market attention and positioning remain active, but valuation pressure is elevated.",
    "diverging": "This narrative is diverging: some support remains, but risk or contradiction signals are rising.",
    "weakening": "This narrative is weakening: support signals are fading or counter-evidence is becoming more important.",
    "dead": "This narrative no longer has enough fresh support in the current evidence set to sustain the thesis.",
}


def interpret_narrative(narrative: dict[str, Any]) -> dict[str, str]:
    state = narrative["state"]
    stage = state["stage"]
    confidence = float(state["confidence"])
    data_quality = state["data_quality"]
    evidence_density = state.get("evidence_density", "none")
    counter_signal_risk = state.get("counter_signal_risk", "unknown")
    dimensions = state["dimensions"]

    return {
        "stage_explanation": STAGE_EXPLANATIONS.get(
            stage,
            "This narrative has an unclassified lifecycle state in the current scoring model.",
        ),
        "risk_explanation": _risk_explanation(dimensions, counter_signal_risk),
        "confidence_note": _confidence_note(
            confidence=confidence,
            evidence_density=evidence_density,
            data_quality=data_quality,
        ),
    }


def _risk_explanation(
    dimensions: dict[str, dict[str, Any]], counter_signal_risk: str
) -> str:
    valuation_score = dimensions["valuation_risk_score"]["score"]
    counter_score = dimensions["counter_evidence_risk_score"]["score"]
    if counter_score >= 70:
        return "counter-evidence is elevated and should be treated as the main pressure point in this narrative review."
    if valuation_score >= 75:
        return "Valuation pressure is elevated, so the narrative may be more sensitive to negative evidence or crowded positioning."
    if counter_signal_risk in {"rising", "watch"}:
        return "Risk signals are present but not yet dominant; the narrative should be monitored for fresh contradiction evidence."
    return "No dominant risk signal is present in the current V1 evidence set."


def _confidence_note(
    confidence: float, evidence_density: str, data_quality: str
) -> str:
    if confidence >= 0.75:
        level = "high"
    elif confidence >= 0.55:
        level = "medium"
    else:
        level = "low"
    return (
        f"Confidence is {level} ({confidence:.2f}) with {evidence_density} evidence density "
        f"and {data_quality} data quality."
    )
