import copy
import json
from pathlib import Path

import pytest
from src.errors import ProviderContractError
from src.modules.narrative_review.promotion import apply_candidate_review_action

FIXTURE_DIR = Path("data/fixtures")


def _registry_payload() -> dict:
    return json.loads((FIXTURE_DIR / "narrative_registry.json").read_text())


def test_approve_candidate_promotes_active_narrative_without_mutating_input():
    registry = _registry_payload()
    original = copy.deepcopy(registry)
    action = {
        "action_id": "ACT_APPROVE_CONSUMER_ELECTRONICS",
        "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "action": "approve",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T10:00:00+00:00",
        "review_note": "Promote as a separate technology hardware theme.",
        "promotion": {
            "narrative_id": "N_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "parent_id": None,
            "level": 2,
            "aliases": [
                "consumer electronics exports",
                "device globalization",
            ],
            "related_terms": [
                "消费电子",
                "终端设备",
                "海外手机",
                "传音控股",
            ],
        },
    }

    result = apply_candidate_review_action(registry, action)

    assert registry == original
    assert result is not registry
    assert result["version"] == "registry-v1"
    promoted = result["narratives"][-1]
    assert promoted == {
        "narrative_id": "N_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "canonical_taxonomy": "Technology Hardware",
        "name": "Consumer Electronics Globalization",
        "canonical_name_zh": "消费电子全球化",
        "canonical_name_en": "Consumer Electronics Globalization",
        "display_name": "消费电子全球化",
        "canonical_taxonomy_zh": "消费电子",
        "canonical_taxonomy_en": "Technology Hardware",
        "parent_id": None,
        "level": 2,
        "status": "active",
        "aliases": ["consumer electronics exports", "device globalization"],
        "aliases_zh": ["consumer electronics exports", "device globalization"],
        "aliases_en": ["consumer electronics exports", "device globalization"],
        "related_terms": ["消费电子", "终端设备", "海外手机", "传音控股"],
        "related_terms_zh": ["消费电子", "终端设备", "海外手机", "传音控股"],
        "related_terms_en": ["消费电子", "终端设备", "海外手机"],
        "definition_zh": "消费电子全球化",
        "definition_en": "Consumer Electronics Globalization",
        "inclusion_criteria_zh": [],
        "exclusion_criteria_zh": [],
        "representative_stocks": ["688036"],
        "human_review_status": "approved",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T10:00:00+00:00",
        "first_seen_at": "2026-05-14",
        "last_updated_at": "2026-05-14",
        "promoted_from_candidate_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "promotion_action_id": "ACT_APPROVE_CONSUMER_ELECTRONICS",
    }
    reviewed_candidate = result["candidate_narratives"][0]
    assert reviewed_candidate["status"] == "promoted"
    assert reviewed_candidate["human_review_status"] == "approved"
    assert reviewed_candidate["reviewed_by"] == "reviewer@example.com"
    assert reviewed_candidate["reviewed_at"] == "2026-05-14T10:00:00+00:00"
    assert reviewed_candidate["review_action_id"] == "ACT_APPROVE_CONSUMER_ELECTRONICS"
    assert reviewed_candidate["promotion_target_id"] == (
        "N_CONSUMER_ELECTRONICS_GLOBALIZATION"
    )
    assert reviewed_candidate["review_note"] == (
        "Promote as a separate technology hardware theme."
    )


def test_reject_candidate_updates_review_state_without_active_promotion():
    registry = _registry_payload()
    action = {
        "action_id": "ACT_REJECT_DATABASE_INFRA",
        "candidate_narrative_id": "C_DOMESTIC_DATABASE_INFRASTRUCTURE",
        "action": "reject",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T11:00:00+00:00",
        "review_note": "Too narrow for the current taxonomy.",
    }

    result = apply_candidate_review_action(registry, action)

    assert len(result["narratives"]) == len(registry["narratives"])
    reviewed_candidate = result["candidate_narratives"][1]
    assert reviewed_candidate["status"] == "rejected"
    assert reviewed_candidate["human_review_status"] == "rejected"
    assert reviewed_candidate["review_action_id"] == "ACT_REJECT_DATABASE_INFRA"
    assert reviewed_candidate["review_note"] == "Too narrow for the current taxonomy."
    assert "promotion_target_id" not in reviewed_candidate


def test_defer_candidate_updates_review_state_for_later_web_queue():
    registry = _registry_payload()
    action = {
        "action_id": "ACT_DEFER_INFRA",
        "candidate_narrative_id": "C_COMMUNICATION_POWER_INFRASTRUCTURE",
        "action": "defer",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T12:00:00+00:00",
        "review_note": "Needs more evidence before taxonomy promotion.",
    }

    result = apply_candidate_review_action(registry, action)

    assert len(result["narratives"]) == len(registry["narratives"])
    reviewed_candidate = result["candidate_narratives"][2]
    assert reviewed_candidate["status"] == "deferred"
    assert reviewed_candidate["human_review_status"] == "deferred"
    assert reviewed_candidate["reviewed_by"] == "reviewer@example.com"
    assert reviewed_candidate["reviewed_at"] == "2026-05-14T12:00:00+00:00"


def test_approve_candidate_requires_promotion_metadata():
    registry = _registry_payload()
    action = {
        "action_id": "ACT_BAD_APPROVE",
        "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "action": "approve",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T10:00:00+00:00",
        "review_note": "Missing promotion target.",
    }

    with pytest.raises(ProviderContractError, match="promotion"):
        apply_candidate_review_action(registry, action)


def test_candidate_review_rejects_unknown_candidate_or_duplicate_narrative_id():
    registry = _registry_payload()
    unknown_action = {
        "action_id": "ACT_UNKNOWN",
        "candidate_narrative_id": "C_UNKNOWN",
        "action": "reject",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T10:00:00+00:00",
        "review_note": "Unknown candidate.",
    }
    duplicate_action = {
        "action_id": "ACT_DUPLICATE",
        "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
        "action": "approve",
        "reviewed_by": "reviewer@example.com",
        "reviewed_at": "2026-05-14T10:00:00+00:00",
        "review_note": "Duplicate active id.",
        "promotion": {
            "narrative_id": "N_SEMI_CAPEX",
            "parent_id": None,
            "level": 2,
            "aliases": [],
            "related_terms": [],
        },
    }

    with pytest.raises(ProviderContractError, match="Unknown candidate"):
        apply_candidate_review_action(registry, unknown_action)
    with pytest.raises(ProviderContractError, match="already exists"):
        apply_candidate_review_action(registry, duplicate_action)
