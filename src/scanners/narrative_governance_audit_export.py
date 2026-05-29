from __future__ import annotations

from typing import Any

from src.scanners.governance_audit import build_governance_audit_export


def build_narrative_governance_audit_export(
    *,
    registry_payload: dict[str, Any],
    service_ledger_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    records = [
        *[
            _narrative_record(item, record_type="narrative")
            for item in _list(registry_payload.get("narratives"))
        ],
        *[
            _narrative_record(item, record_type="candidate_narrative")
            for item in _list(registry_payload.get("candidate_narratives"))
        ],
    ]
    export = build_governance_audit_export(
        record_payload={"version": "narrative-governance-audit-records-v1", "records": records},
        service_ledger_payload=service_ledger_payload,
    )
    return {
        **export,
        "source_registry_version": str(registry_payload.get("version") or ""),
    }


def _narrative_record(item: dict[str, Any], *, record_type: str) -> dict[str, Any]:
    record_id = str(item.get("narrative_id") or item.get("candidate_narrative_id") or "")
    service_approval = str(item.get("service_ledger_approval_id") or "")
    promoted_without_ledger = _promoted_looking(item) and not service_approval
    return {
        "record_type": record_type,
        "record_id": record_id,
        "display_name": str(item.get("display_name") or item.get("name") or record_id),
        "status": str(item.get("status") or "candidate"),
        "trust_status": str(item.get("trust_status") or _default_trust_status(record_type)),
        "human_review_status": str(item.get("human_review_status") or "pending"),
        "review_status": str(item.get("human_review_status") or "pending"),
        "source_store": "reviewed_registry" if record_type == "narrative" else "candidate_registry",
        "service_ledger_approval_id": service_approval,
        "source_count": _source_count(item),
        "promotion_decision": "promoted_without_service_ledger"
        if promoted_without_ledger
        else str(item.get("promotion_action_id") or item.get("review_action_id") or ""),
        "missing_gates": ["service_ledger_approval"] if promoted_without_ledger else [],
        "latest_reviewer": str(item.get("reviewed_by") or ""),
        "updated_at": str(item.get("reviewed_at") or item.get("last_updated_at") or ""),
    }


def _promoted_looking(item: dict[str, Any]) -> bool:
    return (
        str(item.get("status") or "") in {"promoted", "active"}
        and str(item.get("trust_status") or "") == "trusted_validated"
        and str(item.get("human_review_status") or "") == "approved"
    )


def _source_count(item: dict[str, Any]) -> int:
    for key in ("representative_citation_ids", "supporting_source_item_ids"):
        value = item.get(key)
        if isinstance(value, list):
            return len(value)
    citations = item.get("representative_citations")
    if isinstance(citations, list):
        return len(citations)
    return int(item.get("source_item_count") or 0)


def _default_trust_status(record_type: str) -> str:
    return "candidate_untrusted" if record_type == "candidate_narrative" else "untrusted_experimental"


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []
