import pytest
from src.errors import ProviderContractError
from src.modules.narrative_review.queue import build_candidate_review_queue
from src.validation import validate_review_queue_artifact_payload


def test_build_candidate_review_queue_links_candidates_to_exclusions():
    candidate_narratives = [
        {
            "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "name": "Consumer Electronics Globalization",
            "canonical_taxonomy": "Technology Hardware",
            "status": "candidate",
            "source": "mapping_exclusion_review",
            "triggering_stock_codes": ["688036"],
            "related_exclusion_ids": ["EX_SEMI_688036"],
            "aliases": ["consumer electronics exports"],
            "related_terms": ["消费电子", "传音控股"],
            "rationale": "Device exposure candidate.",
            "human_review_status": "candidate",
            "reviewed_by": None,
            "reviewed_at": None,
            "first_seen_at": "2026-05-14",
            "last_updated_at": "2026-05-14",
        }
    ]
    exclusions = [
        {
            "type": "excluded_mapping_candidate",
            "exclusion_id": "EX_SEMI_688036",
            "stock_code": "688036",
            "stock_name": "传音控股",
            "industry": "电子",
            "weight": 0.06,
            "narrative_id": "N_SEMI_CAPEX",
            "narrative_name": "Semiconductor Capex Cycle",
            "method": "registry_term_rule",
            "matched_terms": ["电子"],
            "reason": "Too broad for Semiconductor Capex.",
            "recommended_action": "candidate_narrative_review",
        }
    ]

    queue = build_candidate_review_queue(candidate_narratives, exclusions)

    assert queue == {
        "version": "candidate-review-queue-v1",
        "summary": {
            "total_count": 1,
            "pending_count": 1,
            "action_required": True,
        },
        "items": [
            {
                "review_item_id": "RQ_C_CONSUMER_ELECTRONICS_GLOBALIZATION",
                "item_type": "candidate_narrative",
                "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
                "name": "Consumer Electronics Globalization",
                "canonical_taxonomy": "Technology Hardware",
                "status": "candidate",
                "human_review_status": "candidate",
                "source": "mapping_exclusion_review",
                "rationale": "Device exposure candidate.",
                "triggering_stock_codes": ["688036"],
                "related_exclusion_ids": ["EX_SEMI_688036"],
                "related_exclusions": exclusions,
                "available_actions": ["approve", "reject", "defer"],
                "default_action": "defer",
                "requires_promotion_metadata": True,
                "promotion_action_template": {
                    "action_id": None,
                    "candidate_narrative_id": (
                        "C_CONSUMER_ELECTRONICS_GLOBALIZATION"
                    ),
                    "action": "approve",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "review_note": None,
                    "promotion": {
                        "narrative_id": None,
                        "parent_id": None,
                        "level": 2,
                        "aliases": ["consumer electronics exports"],
                        "related_terms": ["消费电子", "传音控股"],
                    },
                },
            }
        ],
    }


def test_build_candidate_review_queue_handles_empty_candidates():
    assert build_candidate_review_queue([], []) == {
        "version": "candidate-review-queue-v1",
        "summary": {
            "total_count": 0,
            "pending_count": 0,
            "action_required": False,
        },
        "items": [],
    }


def test_validate_review_queue_artifact_payload_rejects_item_count_mismatch():
    payload = {
        "metadata": {"fund_code": "320007"},
        "fund": {"fund_code": "320007", "fund_name": "Test Fund"},
        "provider_foundation": {"provider_mode": "mock"},
        "candidate_narratives": [],
        "excluded_mapping_candidates": [],
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {
                "total_count": 1,
                "pending_count": 0,
                "action_required": False,
            },
            "items": [],
        },
    }

    with pytest.raises(ProviderContractError, match="summary.total_count"):
        validate_review_queue_artifact_payload(payload)


def test_validate_review_queue_artifact_payload_rejects_missing_queue_item():
    payload = {
        "metadata": {"fund_code": "320007"},
        "fund": {"fund_code": "320007", "fund_name": "Test Fund"},
        "provider_foundation": {"provider_mode": "mock"},
        "candidate_narratives": [_candidate_narrative()],
        "excluded_mapping_candidates": [],
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {
                "total_count": 0,
                "pending_count": 0,
                "action_required": False,
            },
            "items": [],
        },
    }

    with pytest.raises(ProviderContractError, match="items must match"):
        validate_review_queue_artifact_payload(payload)


def _candidate_narrative():
    return {
        "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "name": "Consumer Electronics Globalization",
        "canonical_taxonomy": "Technology Hardware",
        "status": "candidate",
        "source": "mapping_exclusion_review",
        "triggering_stock_codes": ["688036"],
        "related_exclusion_ids": ["EX_SEMI_688036"],
        "aliases": ["consumer electronics exports"],
        "related_terms": ["消费电子", "传音控股"],
        "rationale": "Device exposure candidate.",
        "human_review_status": "candidate",
        "reviewed_by": None,
        "reviewed_at": None,
        "first_seen_at": "2026-05-14",
        "last_updated_at": "2026-05-14",
    }
