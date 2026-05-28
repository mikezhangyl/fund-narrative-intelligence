from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stock_narrative_service.config import ServiceConfig


class NarrativeStore:
    def __init__(self, config: ServiceConfig):
        self.config = config

    def registry(self) -> dict[str, Any]:
        return _load_object(self.config.registry_path, label="registry")

    def mappings(self) -> dict[str, Any]:
        return _load_object(self.config.mappings_path, label="mappings")

    def evidence_packs(self) -> dict[str, Any]:
        return _load_object(self.config.evidence_packs_path, label="evidence packs")

    def seed_events(self) -> dict[str, Any]:
        return _load_object(self.config.candidate_events_path, label="candidate events")

    def intake_ledger(self) -> dict[str, Any]:
        path = self.config.intake_ledger_path
        if not path.exists():
            return {"version": "service-intake-events-v1", "events": []}
        return _load_object(path, label="intake ledger")

    def review_actions(self) -> dict[str, Any]:
        path = self.config.review_actions_path
        if not path.exists():
            return {"version": "narrative-review-actions-v0", "items": []}
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

    def review_queue(self) -> dict[str, Any]:
        candidates = self.candidates()["candidate_narratives"]
        latest_actions = _latest_actions_by_candidate(self.review_actions())
        return {
            "version": "narrative-review-queue-v0",
            "items": [
                {
                    "review_item_id": f"IRQ_{candidate['candidate_narrative_id']}",
                    "item_type": "candidate_narrative",
                    "payload_ref": candidate["candidate_narrative_id"],
                    "status": "pending_review",
                    "recommended_action": "human_review_required",
                    "trust_status": "candidate_untrusted",
                    "latest_review_action": latest_actions.get(
                        candidate["candidate_narrative_id"],
                        {},
                    ),
                }
                for candidate in candidates
            ],
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

    def ingest_events(self, payload: dict[str, Any]) -> dict[str, Any]:
        events = _list(payload.get("events"))
        dry_run = bool(payload.get("dry_run"))
        normalized = [_normalize_event(event) for event in events]
        if normalized and not dry_run:
            ledger = self.intake_ledger()
            ledger["events"] = [*_list(ledger.get("events")), *normalized]
            _write_object(self.config.intake_ledger_path, ledger)
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
        reviewed_at = _now()
        decision = {
            "review_action_id": _stable_id(
                "RA",
                [candidate_id, action, reviewed_by, review_note, reviewed_at],
            ),
            "candidate_narrative_id": candidate_id,
            "action": action,
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "review_note": review_note,
            "trust_status_after_action": "candidate_untrusted",
            "promotion_effect": "none",
            "promotion_note": (
                "Review action is recorded only. Trusted promotion requires "
                "separate source, rationale, exclusion, and trust audit gates."
            ),
        }
        actions = self.review_actions()
        actions["items"] = [*_list(actions.get("items")), decision]
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


def _gate(gate_id: str, passed: bool, message: str) -> dict[str, str]:
    return {
        "gate_id": gate_id,
        "status": "passed" if passed else "missing",
        "message": message,
    }


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        **dict(event),
        "event_id": str(event.get("event_id") or _stable_id("EVT", [event])),
        "source_type": str(event.get("source_type") or "unknown"),
        "event_time": str(event.get("event_time") or _now()),
        "candidate_narratives": _list(event.get("candidate_narratives")),
    }


def _candidates_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for event in events:
        for candidate in _list(event.get("candidate_narratives")):
            name = str(candidate.get("name") or candidate.get("narrative_name") or "")
            if not name:
                continue
            candidate_id = str(
                candidate.get("candidate_narrative_id")
                or candidate.get("narrative_id")
                or _stable_id("C_INTAKE", [name])
            )
            candidates[candidate_id] = {
                "candidate_narrative_id": candidate_id,
                "name": name,
                "canonical_taxonomy": str(candidate.get("canonical_taxonomy") or ""),
                "confidence": _float(candidate.get("confidence")),
                "human_review_status": "candidate",
                "trust_status": "candidate_untrusted",
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


def _stable_id(prefix: str, parts: list[Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(parts, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:10].upper()
    return f"{prefix}_{digest}"


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


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
