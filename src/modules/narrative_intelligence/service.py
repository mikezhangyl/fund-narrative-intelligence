from __future__ import annotations

from collections import Counter
from typing import Any

from src.modules.fund_analysis.aggregation import aggregate_fund_narratives
from src.modules.fund_analysis.mapping import build_mapping_result
from src.modules.narrative_intelligence.candidate_generation import (
    build_candidate_seeds,
    build_generated_candidates,
    select_narrative_curator,
)
from src.modules.narrative_intelligence.evidence_synthesizer import (
    synthesize_narrative_evidence,
)
from src.modules.narrative_intelligence.exposure_tags import (
    aggregate_fund_exposure_tags,
    build_company_exposure_tags,
)
from src.modules.narrative_intelligence.mapping_analyst import build_mapping_proposals
from src.modules.narrative_intelligence.model import narrative_display_name
from src.modules.narrative_intelligence.source_scout import build_source_catalog
from src.modules.narrative_review.queue import build_candidate_review_queue
from src.modules.report_writer.interpretation import interpret_narrative
from src.modules.signal_service.scoring import score_narrative_state

LOW_CONFIDENCE_MAPPING_THRESHOLD = 0.6


class NarrativeIntelligenceService:
    def __init__(
        self,
        *,
        holdings: list[dict[str, Any]],
        registry_payload: dict[str, Any],
        mappings: list[dict[str, Any]],
        mapping_exclusions: list[dict[str, Any]] | None = None,
        allow_registry_term_fallback: bool = True,
        enable_narrative_generation: bool = False,
        narrative_curator_mode: str = "auto",
        narrative_curator_model: str = "MiniMax-M2.7",
    ) -> None:
        self._holdings = holdings
        self._registry_payload = registry_payload
        self._mappings = mappings
        self._mapping_exclusions = mapping_exclusions or []
        self._allow_registry_term_fallback = allow_registry_term_fallback
        self._enable_narrative_generation = enable_narrative_generation
        self._narrative_curator_mode = narrative_curator_mode
        self._narrative_curator_model = narrative_curator_model

    def build_context(self) -> dict[str, Any]:
        registry_items = self._registry_payload["narratives"]
        registry_by_id = {item["narrative_id"]: item for item in registry_items}
        mapping_result = build_mapping_result(
            holdings=self._holdings,
            mappings=self._mappings,
            registry=registry_by_id,
            exclusions=self._mapping_exclusions,
            allow_registry_term_fallback=self._allow_registry_term_fallback,
        )
        candidate_narratives = _candidate_narratives_for_excluded_candidates(
            candidate_narratives=self._registry_payload.get("candidate_narratives", []),
            excluded_mapping_candidates=mapping_result["excluded_mapping_candidates"],
        )
        exposures = aggregate_fund_narratives(
            holdings=self._holdings,
            mappings=mapping_result["mappings"],
            registry=registry_by_id,
        )
        return {
            "registry_snapshot": {
                "version": self._registry_payload["version"],
                "narratives": registry_items,
            },
            "mapping_snapshot": {
                "mappings": mapping_result["mappings"],
                "coverage": mapping_result["coverage"],
                "rationales": mapping_result["mapping_rationales"],
                "precision_flags": mapping_result["mapping_precision_flags"],
                "excluded_mapping_candidates": mapping_result[
                    "excluded_mapping_candidates"
                ],
                "unmapped_holdings": mapping_result["unmapped_holdings"],
            },
            "candidate_narratives": candidate_narratives,
            "candidate_review_queue": build_candidate_review_queue(
                candidate_narratives=candidate_narratives,
                excluded_mapping_candidates=mapping_result["excluded_mapping_candidates"],
            ),
            "exposures": exposures,
        }

    def build_snapshot(
        self,
        *,
        evidence: list[dict[str, Any]],
        signal_events: list[dict[str, Any]],
        as_of_date: str,
        data_quality: str,
        announcements_payload: dict[str, Any] | None = None,
        market_quotes_payload: dict[str, Any] | None = None,
        valuation_snapshots_payload: dict[str, Any] | None = None,
        financial_metrics_payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        active_context = context or self.build_context()
        registry_items = active_context["registry_snapshot"]["narratives"]
        registry_by_id = {item["narrative_id"]: item for item in registry_items}
        exposures = active_context["exposures"]
        source_catalog = build_source_catalog(
            holdings=self._holdings,
            evidence=evidence,
            announcements_payload=announcements_payload,
            market_quotes_payload=market_quotes_payload,
            valuation_snapshots_payload=valuation_snapshots_payload,
            financial_metrics_payload=financial_metrics_payload,
        )
        exposure_tag_payload = build_company_exposure_tags(
            holdings=self._holdings,
            company_facts=source_catalog["company_facts"],
        )
        fund_exposure_tag_payload = aggregate_fund_exposure_tags(
            holdings=self._holdings,
            company_exposure_tags=exposure_tag_payload["items"],
            registry_items=registry_items,
        )
        candidate_seed_payload = build_candidate_seeds(
            holdings=self._holdings,
            mapping_snapshot=active_context["mapping_snapshot"],
            source_catalog=source_catalog,
            fund_exposure_tags=fund_exposure_tag_payload["items"],
            registry_snapshot=active_context["registry_snapshot"],
            as_of_date=as_of_date,
        )
        generated_candidate_payload = {
            "version": "generated-candidate-narratives-v1",
            "items": [],
            "failures": [],
            "summary": {
                "generated_candidate_count": 0,
                "failed_candidate_count": 0,
                "attempted_seed_count": 0,
            },
        }
        if self._enable_narrative_generation:
            curator = select_narrative_curator(
                self._narrative_curator_mode,
                model=self._narrative_curator_model,
            )
            generated_candidate_payload = build_generated_candidates(
                candidate_seeds=candidate_seed_payload,
                source_catalog=source_catalog,
                holdings=self._holdings,
                curator=curator,
            )
        generated_candidates = generated_candidate_payload["items"]
        candidate_generation_failures = generated_candidate_payload.get("failures") or []
        combined_candidates = _merge_candidate_narratives(
            active_context["candidate_narratives"],
            generated_candidates,
        )
        candidate_review_queue = build_candidate_review_queue(
            candidate_narratives=combined_candidates,
            excluded_mapping_candidates=active_context["mapping_snapshot"][
                "excluded_mapping_candidates"
            ],
        )
        narrative_results = [
            _with_state(
                exposure=exposure,
                signal_events=signal_events,
                evidence=evidence,
                as_of_date=as_of_date,
                data_quality=data_quality,
            )
            for exposure in exposures
        ]
        narrative_evidence = synthesize_narrative_evidence(
            narrative_results=narrative_results,
            evidence=evidence,
        )
        mapping_proposals = build_mapping_proposals(
            generated_candidates=generated_candidates,
            holdings=self._holdings,
            source_catalog=source_catalog,
        )
        diagnostics = _build_diagnostics(
            holdings=self._holdings,
            registry=registry_by_id,
            mapping_snapshot=active_context["mapping_snapshot"],
            candidate_review_queue=candidate_review_queue,
            evidence=evidence,
            narrative_results=narrative_results,
        )
        return {
            "registry_snapshot": active_context["registry_snapshot"],
            "mapping_snapshot": active_context["mapping_snapshot"],
            "candidate_narratives": combined_candidates,
            "generated_candidate_narratives": generated_candidates,
            "candidate_generation_failures": candidate_generation_failures,
            "candidate_generation_summary": generated_candidate_payload["summary"],
            "candidate_review_queue": candidate_review_queue,
            "primary_narrative": narrative_results[0] if narrative_results else None,
            "secondary_narratives": narrative_results[1:4],
            "all_narratives": narrative_results,
            "source_catalog": source_catalog,
            "company_facts": source_catalog["company_facts"],
            "company_fact_stats": source_catalog["company_fact_stats"],
            "company_exposure_tags": exposure_tag_payload["items"],
            "company_exposure_tag_stats": exposure_tag_payload["stats"],
            "fund_exposure_tags": fund_exposure_tag_payload["items"],
            "fund_exposure_tag_stats": fund_exposure_tag_payload["stats"],
            "candidate_seeds": candidate_seed_payload,
            "mapping_proposals": mapping_proposals,
            "narrative_evidence": narrative_evidence,
            "diagnostics": diagnostics,
        }


def _candidate_narratives_for_excluded_candidates(
    candidate_narratives: list[dict[str, Any]],
    excluded_mapping_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exclusion_ids = {
        str(candidate["exclusion_id"])
        for candidate in excluded_mapping_candidates
        if candidate.get("exclusion_id")
    }
    stock_codes = {
        str(candidate["stock_code"])
        for candidate in excluded_mapping_candidates
        if candidate.get("stock_code")
    }
    return [
        candidate_narrative
        for candidate_narrative in candidate_narratives
        if set(candidate_narrative.get("related_exclusion_ids", [])) & exclusion_ids
        or set(candidate_narrative.get("triggering_stock_codes", [])) & stock_codes
    ]


def _merge_candidate_narratives(
    existing_candidates: list[dict[str, Any]],
    generated_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for candidate in [*existing_candidates, *generated_candidates]:
        candidate_id = str(candidate.get("candidate_narrative_id") or "")
        if not candidate_id:
            continue
        if candidate_id not in merged:
            merged[candidate_id] = candidate
            continue
        current = merged[candidate_id]
        current["triggering_stock_codes"] = sorted(
            {
                *current.get("triggering_stock_codes", []),
                *candidate.get("triggering_stock_codes", []),
            }
        )
        current["related_exclusion_ids"] = sorted(
            {
                *current.get("related_exclusion_ids", []),
                *candidate.get("related_exclusion_ids", []),
            }
        )
    return list(merged.values())


def _with_state(
    *,
    exposure: dict[str, Any],
    signal_events: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    as_of_date: str,
    data_quality: str,
) -> dict[str, Any]:
    narrative_id = exposure["narrative_id"]
    evidence_count = sum(1 for item in evidence if item["narrative_id"] == narrative_id)
    result = {
        **exposure,
        "state": score_narrative_state(
            narrative_id=narrative_id,
            signal_events=signal_events,
            mapping_confidence=exposure["confidence"],
            evidence_count=evidence_count,
            as_of_date=as_of_date,
            data_quality=data_quality,
        ),
    }
    result["interpretation"] = interpret_narrative(result)
    return result


def _build_diagnostics(
    *,
    holdings: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
    mapping_snapshot: dict[str, Any],
    candidate_review_queue: dict[str, Any],
    evidence: list[dict[str, Any]],
    narrative_results: list[dict[str, Any]],
) -> dict[str, Any]:
    low_confidence_mappings = _low_confidence_mappings(
        holdings=holdings,
        registry=registry,
        mappings=mapping_snapshot["mappings"],
    )
    missing_evidence_narratives = _missing_evidence_narratives(
        evidence=evidence,
        narrative_results=narrative_results,
    )
    conflicting_evidence_narratives = _conflicting_evidence_narratives(
        evidence=evidence,
        narrative_results=narrative_results,
    )
    summary = {
        "unmapped_holding_count": len(mapping_snapshot["unmapped_holdings"]),
        "low_confidence_mapping_count": len(low_confidence_mappings),
        "missing_evidence_narrative_count": len(missing_evidence_narratives),
        "conflicting_evidence_narrative_count": len(conflicting_evidence_narratives),
        "action_required": any(
            [
                bool(mapping_snapshot["unmapped_holdings"]),
                bool(low_confidence_mappings),
                bool(missing_evidence_narratives),
                bool(conflicting_evidence_narratives),
                bool(candidate_review_queue["summary"]["action_required"]),
            ]
        ),
    }
    return {
        "version": "narrative-intelligence-diagnostics-v1",
        "summary": summary,
        "unmapped_holdings": mapping_snapshot["unmapped_holdings"],
        "low_confidence_mappings": low_confidence_mappings,
        "missing_evidence_narratives": missing_evidence_narratives,
        "conflicting_evidence_narratives": conflicting_evidence_narratives,
    }


def _low_confidence_mappings(
    *,
    holdings: list[dict[str, Any]],
    registry: dict[str, dict[str, Any]],
    mappings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    holdings_by_stock = {holding["stock_code"]: holding for holding in holdings}
    diagnostics = []
    for mapping in mappings:
        confidence = float(mapping.get("confidence", 0))
        needs_review = bool(mapping.get("needs_review", False))
        if confidence >= LOW_CONFIDENCE_MAPPING_THRESHOLD and not needs_review:
            continue
        holding = holdings_by_stock.get(mapping["stock_code"], {})
        narrative_id = mapping["narrative_id"]
        diagnostics.append(
            {
                "stock_code": mapping["stock_code"],
                "stock_name": holding.get("stock_name"),
                "industry": holding.get("industry"),
                "weight": holding.get("weight"),
                "narrative_id": narrative_id,
                "narrative_name": narrative_display_name(
                    registry.get(narrative_id, {}),
                    narrative_id,
                ),
                "method": mapping.get("method"),
                "confidence": confidence,
                "mapping_weight": float(mapping.get("mapping_weight", 0)),
                "needs_review": needs_review,
                "precision_flag": mapping.get("precision_flag"),
            }
        )
    return diagnostics


def _missing_evidence_narratives(
    *,
    evidence: list[dict[str, Any]],
    narrative_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_counts = Counter(
        str(item["narrative_id"])
        for item in evidence
        if item.get("narrative_id")
    )
    return [
        {
            "narrative_id": narrative["narrative_id"],
            "name": narrative_display_name(
                narrative,
                narrative["narrative_id"],
            ),
            "normalized_exposure": narrative["normalized_exposure"],
            "raw_exposure": narrative["raw_exposure"],
            "evidence_count": 0,
        }
        for narrative in narrative_results
        if evidence_counts.get(narrative["narrative_id"], 0) == 0
        and _narrative_signal_support_count(narrative) == 0
    ]


def _conflicting_evidence_narratives(
    *,
    evidence: list[dict[str, Any]],
    narrative_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_counts: dict[str, Counter[str]] = {}
    for item in evidence:
        narrative_id = item.get("narrative_id")
        sentiment = item.get("sentiment")
        if not narrative_id or sentiment not in {"positive", "negative"}:
            continue
        counter = evidence_counts.setdefault(str(narrative_id), Counter())
        counter[str(sentiment)] += 1
    conflicts = []
    for narrative in narrative_results:
        counts = evidence_counts.get(narrative["narrative_id"])
        if not counts or counts.get("positive", 0) == 0 or counts.get("negative", 0) == 0:
            continue
        conflicts.append(
            {
                "narrative_id": narrative["narrative_id"],
                "name": narrative_display_name(
                    narrative,
                    narrative["narrative_id"],
                ),
                "positive_evidence_count": counts["positive"],
                "negative_evidence_count": counts["negative"],
            }
        )
    return conflicts


def _narrative_signal_support_count(narrative: dict[str, Any]) -> int:
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
