from __future__ import annotations

from collections import Counter
from typing import Any

NARRATIVE_EVIDENCE_VERSION = "narrative-evidence-summary-v1"


def synthesize_narrative_evidence(
    *,
    narrative_results: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_by_narrative: dict[str, list[dict[str, Any]]] = {}
    for item in evidence:
        narrative_id = str(item.get("narrative_id") or "")
        if narrative_id:
            evidence_by_narrative.setdefault(narrative_id, []).append(item)
    summaries = []
    for narrative in narrative_results:
        narrative_id = narrative["narrative_id"]
        narrative_evidence = evidence_by_narrative.get(narrative_id, [])
        signal_evidence_count = _signal_evidence_count(narrative)
        sentiment_counts = Counter(
            str(item.get("sentiment") or "mixed") for item in narrative_evidence
        )
        effective_evidence_count = len(narrative_evidence) or signal_evidence_count
        mixed_count = sentiment_counts.get("mixed", 0)
        if len(narrative_evidence) == 0 and signal_evidence_count > 0:
            mixed_count = signal_evidence_count
        summaries.append(
            {
                "narrative_id": narrative_id,
                "name": narrative.get("name"),
                "evidence_count": effective_evidence_count,
                "direct_evidence_count": len(narrative_evidence),
                "signal_evidence_count": signal_evidence_count,
                "positive_count": sentiment_counts.get("positive", 0),
                "negative_count": sentiment_counts.get("negative", 0),
                "mixed_count": mixed_count,
                "support_status": _support_status(
                    sentiment_counts,
                    direct_evidence_count=len(narrative_evidence),
                    signal_evidence_count=signal_evidence_count,
                ),
                "latest_event_date": max(
                    (str(item.get("event_date") or "") for item in narrative_evidence),
                    default=None,
                ),
                "representative_evidence_ids": [
                    str(item.get("evidence_id"))
                    for item in sorted(
                        narrative_evidence,
                        key=lambda item: (
                            float(item.get("confidence") or 0),
                            str(item.get("event_date") or ""),
                        ),
                        reverse=True,
                    )[:3]
                ],
            }
        )
    return {
        "version": NARRATIVE_EVIDENCE_VERSION,
        "items": summaries,
        "summary": {
            "narrative_count": len(summaries),
            "conflicting_count": len(
                [item for item in summaries if item["support_status"] == "conflicting"]
            ),
            "missing_count": len(
                [item for item in summaries if item["support_status"] == "missing"]
            ),
        },
    }


def _support_status(
    sentiment_counts: Counter[str],
    *,
    direct_evidence_count: int,
    signal_evidence_count: int,
) -> str:
    if direct_evidence_count == 0 and signal_evidence_count == 0:
        return "missing"
    if sentiment_counts.get("positive", 0) and sentiment_counts.get("negative", 0):
        return "conflicting"
    if direct_evidence_count >= 2:
        return "corroborated"
    return "limited"


def _signal_evidence_count(narrative: dict[str, Any]) -> int:
    state = narrative.get("state")
    if not isinstance(state, dict):
        return 0
    dimensions = state.get("dimensions")
    if not isinstance(dimensions, dict):
        return 0
    return sum(
        int(dimension.get("supporting_signal_count", 0))
        + int(dimension.get("risk_signal_count", 0))
        for dimension in dimensions.values()
        if isinstance(dimension, dict)
    )
