from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.errors import ProviderContractError
from src.validation import validate_registry_payload

REVIEW_ACTIONS = {"approve", "reject", "defer"}
REVIEW_STATUS_BY_ACTION = {
    "approve": "approved",
    "reject": "rejected",
    "defer": "deferred",
}
CANDIDATE_STATUS_BY_ACTION = {
    "approve": "promoted",
    "reject": "rejected",
    "defer": "deferred",
}


def apply_candidate_review_action(
    registry_payload: dict[str, Any],
    action_payload: dict[str, Any],
) -> dict[str, Any]:
    """Apply one explicit human review action to a candidate narrative registry."""
    validate_registry_payload(registry_payload)
    _validate_action_payload(action_payload)

    candidate_id = action_payload["candidate_narrative_id"]
    candidate_index = _candidate_index(registry_payload, candidate_id)
    if candidate_index is None:
        raise ProviderContractError(f"Unknown candidate narrative: {candidate_id}")

    action = action_payload["action"]
    result = deepcopy(registry_payload)
    candidate = result["candidate_narratives"][candidate_index]
    reviewed_candidate = _reviewed_candidate(candidate, action_payload)
    result["candidate_narratives"][candidate_index] = reviewed_candidate

    if action == "approve":
        promoted = _promoted_narrative(candidate, action_payload, registry_payload)
        result["narratives"] = [*result["narratives"], promoted]
        result["candidate_narratives"][candidate_index] = {
            **reviewed_candidate,
            "promotion_target_id": promoted["narrative_id"],
        }

    validate_registry_payload(result)
    return result


def _validate_action_payload(action_payload: dict[str, Any]) -> None:
    if not isinstance(action_payload, dict):
        raise ProviderContractError("review action must be an object")
    required = {
        "action_id",
        "candidate_narrative_id",
        "action",
        "reviewed_by",
        "reviewed_at",
        "review_note",
    }
    missing = sorted(required - set(action_payload))
    if missing:
        raise ProviderContractError(f"review action missing required fields: {missing}")
    if action_payload["action"] not in REVIEW_ACTIONS:
        raise ProviderContractError(
            f"review action must be one of: {sorted(REVIEW_ACTIONS)}"
        )
    for field in required:
        if not isinstance(action_payload[field], str) or not action_payload[field]:
            raise ProviderContractError(f"review action {field} must be a non-empty string")
    if action_payload["action"] == "approve":
        _validate_promotion_payload(action_payload.get("promotion"))


def _validate_promotion_payload(promotion: Any) -> None:
    if not isinstance(promotion, dict):
        raise ProviderContractError("approval action requires promotion metadata")
    required = {"narrative_id", "parent_id", "level", "aliases", "related_terms"}
    missing = sorted(required - set(promotion))
    if missing:
        raise ProviderContractError(f"promotion missing required fields: {missing}")
    if not isinstance(promotion["narrative_id"], str) or not promotion["narrative_id"]:
        raise ProviderContractError("promotion narrative_id must be a non-empty string")
    if promotion["parent_id"] is not None and not isinstance(promotion["parent_id"], str):
        raise ProviderContractError("promotion parent_id must be null or a string")
    if not isinstance(promotion["level"], int) or promotion["level"] <= 0:
        raise ProviderContractError("promotion level must be a positive integer")
    _require_string_list(promotion["aliases"], "promotion aliases")
    _require_string_list(promotion["related_terms"], "promotion related_terms")


def _reviewed_candidate(
    candidate: dict[str, Any],
    action_payload: dict[str, Any],
) -> dict[str, Any]:
    action = action_payload["action"]
    return {
        **candidate,
        "status": CANDIDATE_STATUS_BY_ACTION[action],
        "human_review_status": REVIEW_STATUS_BY_ACTION[action],
        "reviewed_by": action_payload["reviewed_by"],
        "reviewed_at": action_payload["reviewed_at"],
        "last_updated_at": action_payload["reviewed_at"][:10],
        "review_action_id": action_payload["action_id"],
        "review_note": action_payload["review_note"],
    }


def _promoted_narrative(
    candidate: dict[str, Any],
    action_payload: dict[str, Any],
    registry_payload: dict[str, Any],
) -> dict[str, Any]:
    promotion = action_payload["promotion"]
    narrative_id = promotion["narrative_id"]
    existing_ids = {narrative["narrative_id"] for narrative in registry_payload["narratives"]}
    if narrative_id in existing_ids:
        raise ProviderContractError(f"narrative_id already exists: {narrative_id}")
    reviewed_at = action_payload["reviewed_at"]
    return {
        "narrative_id": narrative_id,
        "canonical_taxonomy": candidate["canonical_taxonomy"],
        "name": candidate["name"],
        "parent_id": promotion["parent_id"],
        "level": promotion["level"],
        "status": "active",
        "aliases": promotion["aliases"],
        "related_terms": promotion["related_terms"],
        "human_review_status": "approved",
        "reviewed_by": action_payload["reviewed_by"],
        "reviewed_at": reviewed_at,
        "first_seen_at": candidate["first_seen_at"],
        "last_updated_at": reviewed_at[:10],
        "promoted_from_candidate_id": candidate["candidate_narrative_id"],
        "promotion_action_id": action_payload["action_id"],
    }


def _candidate_index(
    registry_payload: dict[str, Any],
    candidate_id: str,
) -> int | None:
    for index, candidate in enumerate(registry_payload.get("candidate_narratives", [])):
        if candidate.get("candidate_narrative_id") == candidate_id:
            return index
    return None


def _require_string_list(value: Any, context: str) -> None:
    if not isinstance(value, list):
        raise ProviderContractError(f"{context} must be a list")
    if not all(isinstance(item, str) for item in value):
        raise ProviderContractError(f"{context} must contain strings only")
