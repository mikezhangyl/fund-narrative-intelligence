from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stock_narrative_service.config import ServiceConfig
from stock_narrative_service.identity import (
    candidate_mapping_identity,
    candidate_narrative_identity,
    evidence_pack_identity,
    review_action_identity,
    source_event_identity,
)

INTAKE_LEDGER_VERSION = "service-intake-events-v1"
REVIEW_ACTION_LEDGER_VERSION = "narrative-review-actions-v1"


class NarrativeStore:
    def __init__(self, config: ServiceConfig):
        self.config = config

    def registry(self) -> dict[str, Any]:
        return _load_object(self.config.registry_path, label="registry")

    def mappings(self) -> dict[str, Any]:
        return _load_object(self.config.mappings_path, label="mappings")

    def evidence_packs(self) -> dict[str, Any]:
        payload = _load_object(self.config.evidence_packs_path, label="evidence packs")
        return _evidence_packs_with_identity(payload)

    def seed_events(self) -> dict[str, Any]:
        return _load_object(self.config.candidate_events_path, label="candidate events")

    def intake_ledger(self) -> dict[str, Any]:
        path = self.config.intake_ledger_path
        if not path.exists():
            return {"version": INTAKE_LEDGER_VERSION, "events": []}
        return _load_object(path, label="intake ledger")

    def review_actions(self) -> dict[str, Any]:
        path = self.config.review_actions_path
        if not path.exists():
            return {"version": REVIEW_ACTION_LEDGER_VERSION, "items": []}
        return _load_object(path, label="review actions")

    def candidates(self) -> dict[str, Any]:
        registry_candidates = _list(self.registry().get("candidate_narratives"))
        intake_candidates = _candidates_from_events(_all_events(self))
        candidates_by_id = {
            str(item.get("candidate_narrative_id")): item
            for item in [*registry_candidates, *intake_candidates]
            if item.get("candidate_narrative_id")
        }
        return {
            "candidate_narratives": sorted(
                candidates_by_id.values(),
                key=lambda item: str(item.get("candidate_narrative_id") or ""),
            )
        }

    def review_queue(self, *, status: str = "") -> dict[str, Any]:
        candidates = self.candidates()["candidate_narratives"]
        latest_actions = _latest_actions_by_candidate(self.review_actions())
        items = [
            _review_queue_item(
                candidate=candidate,
                latest_action=latest_actions.get(
                    candidate["candidate_narrative_id"],
                    {},
                ),
            )
            for candidate in candidates
        ]
        if status:
            items = [item for item in items if item["status"] == status]
        return {
            "version": "narrative-review-queue-v0",
            "filter": {"status": status},
            "summary": _queue_summary(items),
            "items": items,
        }

    def trust_audit_latest(self) -> dict[str, Any]:
        registry_trust = _trust_status(self.registry())
        mapping_trust = _trust_status(self.mappings())
        evidence_trust = str(self.evidence_packs().get("trust_status") or "unspecified")
        blocking = [
            label
            for label, status in {
                "registry": registry_trust,
                "mappings": mapping_trust,
                "evidence_packs": evidence_trust,
            }.items()
            if status not in {"trusted_validated"}
        ]
        return {
            "version": "narrative-trust-audit-v0",
            "result": "passed" if not blocking else "blocked",
            "registry_trust_status": registry_trust,
            "mapping_trust_status": mapping_trust,
            "evidence_pack_trust_status": evidence_trust,
            "blocking_scopes": blocking,
            "generated_at": _now(),
        }

    def ops_summary(self) -> dict[str, Any]:
        registry = self.registry()
        mappings = self.mappings()
        evidence = self.evidence_packs()
        candidates = self.candidates()
        review_queue = self.review_queue()
        review_actions = self.review_actions()
        trust_audit = self.trust_audit_latest()
        return {
            "version": "narrative-service-ops-summary-v0",
            "generated_at": _now(),
            "summary": {
                "narrative_count": len(_list(registry.get("narratives"))),
                "candidate_narrative_count": len(
                    _list(candidates.get("candidate_narratives"))
                ),
                "stock_mapping_count": len(_list(mappings.get("mappings"))),
                "evidence_pack_count": len(_list(evidence.get("packs"))),
                "review_action_count": len(_list(review_actions.get("items"))),
            },
            "trust_status": {
                "registry": _trust_status(registry),
                "mappings": _trust_status(mappings),
                "evidence_packs": str(evidence.get("trust_status") or "unspecified"),
            },
            "review_queue_summary": review_queue["summary"],
            "trust_audit": {
                "result": trust_audit["result"],
                "blocking_scopes": trust_audit["blocking_scopes"],
            },
        }

    def ingest_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        events = _event_list(payload.get("events"))
        dry_run = bool(payload.get("dry_run"))
        if events and not dry_run:
            ledger = self.intake_ledger()
            existing_events = _list(ledger.get("events"))
            normalized = [
                _normalize_event(
                    event,
                    ledger_sequence=len(existing_events) + index + 1,
                )
                for index, event in enumerate(events)
            ]
            ledger = {
                **ledger,
                "version": INTAKE_LEDGER_VERSION,
                "events": [*existing_events, *normalized],
            }
            _write_object(self.config.intake_ledger_path, ledger)
        else:
            normalized = [_normalize_event(event) for event in events]
        candidates = _candidates_from_events(normalized)
        return {
            "ingested_event_count": len(normalized),
            "dry_run": dry_run,
            "candidate_narratives": candidates,
            "review_queue_items": [
                {
                    "review_item_id": f"IRQ_{candidate['candidate_narrative_id']}",
                    "item_type": "candidate_narrative",
                    "payload_ref": candidate["candidate_narrative_id"],
                    "status": "pending_review",
                    "recommended_action": "human_review_required",
                    "trust_status": "candidate_untrusted",
                }
                for candidate in candidates
            ],
        }

    def apply_review_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(payload.get("candidate_narrative_id") or "").strip()
        action = str(payload.get("action") or "").strip()
        reviewed_by = str(payload.get("reviewed_by") or "").strip()
        review_note = str(payload.get("review_note") or "").strip()
        if not candidate_id:
            raise ValueError("candidate_narrative_id is required")
        if action not in {"approve", "reject", "defer"}:
            raise ValueError("action must be approve, reject, or defer")
        if not reviewed_by:
            raise ValueError("reviewed_by is required")
        if not review_note:
            raise ValueError("review_note is required")
        candidate_ids = {
            str(candidate.get("candidate_narrative_id") or "")
            for candidate in self.candidates()["candidate_narratives"]
        }
        if candidate_id not in candidate_ids:
            raise ValueError(f"Unknown candidate_narrative_id: {candidate_id}")
        actions = self.review_actions()
        existing_actions = _list(actions.get("items"))
        idempotency_key = str(payload.get("idempotency_key") or "").strip()
        review_action_id, identity_metadata = review_action_identity(
            candidate_narrative_id=candidate_id,
            action=action,
            reviewed_by=reviewed_by,
            review_note=review_note,
            reviewed_at="",
            idempotency_key=idempotency_key,
        )
        if idempotency_key:
            existing = _review_action_by_id(existing_actions, review_action_id)
            if existing is not None:
                return {"decision": {**existing, "idempotent_replay": True}}
        reviewed_at = _now()
        if not idempotency_key:
            review_action_id, identity_metadata = review_action_identity(
                candidate_narrative_id=candidate_id,
                action=action,
                reviewed_by=reviewed_by,
                review_note=review_note,
                reviewed_at=reviewed_at,
            )
        decision = {
            "schema_version": "review-action-ledger-record-v1",
            "ledger_record_type": "review_action",
            "ledger_sequence": len(existing_actions) + 1,
            "recorded_at": reviewed_at,
            "review_action_id": review_action_id,
            "candidate_narrative_id": candidate_id,
            "action": action,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "review_note": review_note,
            "idempotency_key": idempotency_key,
            "identity_metadata": identity_metadata,
            "source_metadata": _mapping(payload.get("source_metadata")),
            "trust_status_after_action": "candidate_untrusted",
            "promotion_effect": "none",
            "promotion_note": (
                "Review action is recorded only. Trusted promotion requires "
                "separate source, rationale, exclusion, and trust audit gates."
            ),
        }
        actions = {
            **actions,
            "version": REVIEW_ACTION_LEDGER_VERSION,
            "items": [*existing_actions, decision],
        }
        _write_object(self.config.review_actions_path, actions)
        return {"decision": decision}

    def promotion_preflight(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(payload.get("candidate_narrative_id") or "").strip()
        if not candidate_id:
            raise ValueError("candidate_narrative_id is required")
        candidate = _candidate_by_id(self.candidates(), candidate_id)
        if candidate is None:
            raise ValueError(f"Unknown candidate_narrative_id: {candidate_id}")
        latest_action = _latest_actions_by_candidate(self.review_actions()).get(
            candidate_id,
            {},
        )
        gates = _promotion_gates(candidate=candidate, latest_action=latest_action)
        missing_gates = [
            gate["gate_id"] for gate in gates if gate["status"] != "passed"
        ]
        return {
            "version": "narrative-promotion-preflight-v0",
            "candidate_narrative_id": candidate_id,
            "result": "blocked" if missing_gates else "ready_for_trust_audit",
            "missing_gates": missing_gates,
            "gates": gates,
            "latest_review_action": latest_action,
            "promotion_effect": "none",
            "trust_status_after_preflight": "candidate_untrusted",
        }


def _all_events(store: NarrativeStore) -> list[dict[str, Any]]:
    return [
        *_list(store.seed_events().get("events")),
        *_list(store.intake_ledger().get("events")),
    ]


def _candidate_by_id(
    payload: dict[str, Any],
    candidate_id: str,
) -> dict[str, Any] | None:
    for candidate in _list(payload.get("candidate_narratives")):
        if str(candidate.get("candidate_narrative_id") or "") == candidate_id:
            return candidate
    return None


def _latest_actions_by_candidate(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for item in _list(payload.get("items")):
        candidate_id = str(item.get("candidate_narrative_id") or "")
        if candidate_id:
            latest[candidate_id] = item
    return latest


def _review_action_by_id(
    actions: list[dict[str, Any]],
    review_action_id: str,
) -> dict[str, Any] | None:
    for item in actions:
        if str(item.get("review_action_id") or "") == review_action_id:
            return item
    return None


def _promotion_gates(
    *,
    candidate: dict[str, Any],
    latest_action: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _gate(
            "source_evidence",
            bool(
                _list(candidate.get("representative_citations"))
                or _list(candidate.get("representative_citation_ids"))
                or _list(
                    _mapping(candidate.get("derivation")).get(
                        "supporting_source_item_ids",
                    )
                )
            ),
            "Candidate needs representative citations or source item links.",
        ),
        _gate(
            "mapping_rationale",
            bool(str(candidate.get("rationale") or "").strip()),
            "Candidate needs explicit narrative rationale.",
        ),
        _gate(
            "exclusion_criteria",
            bool(
                _list(candidate.get("exclusion_criteria"))
                or _list(candidate.get("exclusion_criteria_zh"))
            ),
            "Candidate needs exclusion criteria before trust audit.",
        ),
        _gate(
            "service_review_approval",
            str(latest_action.get("action") or "") == "approve",
            "Candidate needs an approve action in the service review ledger.",
        ),
    ]


def _review_queue_item(
    *,
    candidate: dict[str, Any],
    latest_action: dict[str, Any],
) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_narrative_id"])
    gates = _promotion_gates(candidate=candidate, latest_action=latest_action)
    missing_gates = [gate["gate_id"] for gate in gates if gate["status"] != "passed"]
    status, recommended_action = _review_status(
        latest_action=latest_action,
        missing_gates=missing_gates,
    )
    return {
        "review_item_id": f"IRQ_{candidate_id}",
        "item_type": "candidate_narrative",
        "payload_ref": candidate_id,
        "status": status,
        "recommended_action": recommended_action,
        "trust_status": "candidate_untrusted",
        "preflight_result": "blocked" if missing_gates else "ready_for_trust_audit",
        "missing_gates": missing_gates,
        "latest_review_action": latest_action,
    }


def _review_status(
    *,
    latest_action: dict[str, Any],
    missing_gates: list[str],
) -> tuple[str, str]:
    action = str(latest_action.get("action") or "")
    if action == "reject":
        return "rejected", "no_action"
    if action == "defer":
        return "deferred", "revisit_later"
    if action == "approve":
        if missing_gates:
            return "approved_blocked_by_evidence", "complete_missing_gates"
        return "ready_for_trust_audit", "run_trust_audit"
    return "pending_review", "human_review_required"


def _queue_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "pending_review": 0,
        "ready_for_trust_audit": 0,
        "approved_blocked_by_evidence": 0,
        "rejected": 0,
        "deferred": 0,
    }
    for item in items:
        status = str(item.get("status") or "")
        summary[status] = summary.get(status, 0) + 1
    return summary


def _gate(gate_id: str, passed: bool, message: str) -> dict[str, str]:
    return {
        "gate_id": gate_id,
        "status": "passed" if passed else "missing",
        "message": message,
    }


def _normalize_event(
    event: dict[str, Any],
    *,
    ledger_sequence: int | None = None,
) -> dict[str, Any]:
    event_id, identity_metadata = source_event_identity(event)
    normalized = {
        **dict(event),
        "event_id": event_id,
        "identity_metadata": identity_metadata,
        "source_type": str(event.get("source_type") or "unknown"),
        "event_time": str(event.get("event_time") or _now()),
        "source_metadata": _mapping(event.get("source_metadata")),
        "candidate_narratives": _list(event.get("candidate_narratives")),
    }
    if ledger_sequence is None:
        return normalized
    return {
        **normalized,
        "schema_version": "candidate-intake-ledger-record-v1",
        "ledger_record_type": "candidate_intake_event",
        "ledger_sequence": ledger_sequence,
        "recorded_at": _now(),
        "promotion_effect": "none",
    }


def _candidates_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for event in events:
        for candidate in _list(event.get("candidate_narratives")):
            name = str(candidate.get("name") or candidate.get("narrative_name") or "")
            if not name:
                continue
            candidate_id, identity_metadata = candidate_narrative_identity(candidate)
            candidates[candidate_id] = {
                "candidate_narrative_id": candidate_id,
                "name": name,
                "canonical_taxonomy": str(candidate.get("canonical_taxonomy") or ""),
                "confidence": _float(candidate.get("confidence")),
                "human_review_status": "candidate",
                "trust_status": "candidate_untrusted",
                "identity_metadata": identity_metadata,
                "source_event_ids": sorted(
                    {
                        *candidates.get(candidate_id, {}).get("source_event_ids", []),
                        str(event.get("event_id") or ""),
                    }
                ),
            }
    return sorted(candidates.values(), key=lambda item: item["candidate_narrative_id"])


def _trust_status(payload: dict[str, Any]) -> str:
    metadata = payload.get("trust_metadata")
    if isinstance(metadata, dict):
        return str(metadata.get("trust_status") or "unspecified")
    return str(payload.get("trust_status") or "unspecified")


def _evidence_packs_with_identity(payload: dict[str, Any]) -> dict[str, Any]:
    packs = []
    for pack in _list(payload.get("packs")):
        stock_code = str(pack.get("stock_code") or "")
        mappings = []
        for mapping in _list(pack.get("proposed_mappings")):
            narrative_id = str(mapping.get("narrative_id") or "")
            evidence_pack_id, evidence_identity = evidence_pack_identity(
                stock_code,
                narrative_id,
            )
            candidate_mapping_id, mapping_identity = candidate_mapping_identity(
                stock_code,
                narrative_id,
            )
            mappings.append(
                {
                    **mapping,
                    "evidence_pack_id": evidence_pack_id,
                    "candidate_mapping_id": candidate_mapping_id,
                    "identity_metadata": mapping_identity,
                    "evidence_pack_identity_metadata": evidence_identity,
                }
            )
        packs.append({**pack, "proposed_mappings": mappings})
    return {**payload, "packs": packs}


def _load_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return deepcopy(payload)


def _write_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _event_list(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("events must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError("events must contain JSON objects")
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
