from __future__ import annotations

from typing import Any


def build_candidate_review_queue(
    candidate_narratives: list[dict[str, Any]],
    excluded_mapping_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    items = [
        _queue_item(
            candidate=candidate,
            related_exclusions=_related_exclusions(
                candidate=candidate,
                exclusions=excluded_mapping_candidates,
            ),
        )
        for candidate in candidate_narratives
    ]
    pending_count = sum(
        1 for item in items if item["human_review_status"] == "candidate"
    )
    return {
        "version": "candidate-review-queue-v1",
        "summary": {
            "total_count": len(items),
            "pending_count": pending_count,
            "action_required": pending_count > 0,
        },
        "items": items,
    }


def _queue_item(
    candidate: dict[str, Any],
    related_exclusions: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_id = candidate["candidate_narrative_id"]
    return {
        "review_item_id": f"RQ_{candidate_id}",
        "item_type": "candidate_narrative",
        "candidate_narrative_id": candidate_id,
        "name": candidate["name"],
        "canonical_taxonomy": candidate["canonical_taxonomy"],
        "status": candidate["status"],
        "human_review_status": candidate["human_review_status"],
        "source": candidate["source"],
        "rationale": candidate["rationale"],
        "triggering_stock_codes": candidate.get("triggering_stock_codes", []),
        "related_exclusion_ids": candidate.get("related_exclusion_ids", []),
        "related_exclusions": related_exclusions,
        "available_actions": ["approve", "reject", "defer"],
        "default_action": "defer",
        "requires_promotion_metadata": True,
        "promotion_action_template": {
            "action_id": None,
            "candidate_narrative_id": candidate_id,
            "action": "approve",
            "reviewed_by": None,
            "reviewed_at": None,
            "review_note": None,
            "promotion": {
                "narrative_id": None,
                "parent_id": None,
                "level": 2,
                "aliases": candidate.get("aliases", []),
                "related_terms": candidate.get("related_terms", []),
            },
        },
    }


def _related_exclusions(
    candidate: dict[str, Any],
    exclusions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    related_exclusion_ids = set(candidate.get("related_exclusion_ids", []))
    triggering_stock_codes = set(candidate.get("triggering_stock_codes", []))
    return [
        exclusion
        for exclusion in exclusions
        if exclusion.get("exclusion_id") in related_exclusion_ids
        or exclusion.get("stock_code") in triggering_stock_codes
    ]
