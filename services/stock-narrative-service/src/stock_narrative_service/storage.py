from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from stock_narrative_service.config import ServiceConfig
from stock_narrative_service.diagnostics import operational_diagnostics
from stock_narrative_service.identity import (
    candidate_mapping_identity,
    candidate_narrative_identity,
    evidence_pack_identity,
    promotion_decision_identity,
    review_action_identity,
    source_event_identity,
    stable_id,
)
from stock_narrative_service.radar import (
    radar_bubbles,
    radar_contract,
    radar_evidence_detail,
    radar_mined_candidates,
    radar_scores,
    radar_source_signals,
)

INTAKE_LEDGER_VERSION = "service-intake-events-v1"
REVIEW_ACTION_LEDGER_VERSION = "narrative-review-actions-v1"
PROMOTION_DECISION_LEDGER_VERSION = "narrative-promotion-decisions-v1"
PROVIDER_PREFERENCE_BY_SOURCE_TYPE = {
    "news": ["gateway_news_briefs", "tushare_news"],
    "announcement": ["gateway_announcements", "tushare_announcements"],
    "manual": ["manual_research_note"],
    "social_future": ["reserved_social_connector"],
}
SOURCE_MODE_BY_SOURCE_TYPE = {
    "news": "gateway_or_tushare_preferred",
    "announcement": "gateway_or_tushare_preferred",
    "manual": "manual_research_note",
    "social_future": "reserved_future_connector",
}
PROMOTION_ATOMIC_WRITE_SET = [
    "trusted_registry_record",
    "trusted_stock_mapping_record",
    "trusted_evidence_pack_record",
    "promotion_decision_ledger_record",
]


class PromotionGateError(ValueError):
    def __init__(self, *, candidate_id: str, missing_gates: list[str]):
        self.candidate_id = candidate_id
        self.missing_gates = missing_gates
        super().__init__(f"Promotion gates missing: {', '.join(missing_gates)}")


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

    def evidence_pack_detail(
        self,
        *,
        evidence_pack_id: str = "",
        stock_code: str = "",
        narrative_id: str = "",
    ) -> dict[str, Any] | None:
        evidence_pack_id = str(evidence_pack_id or "").strip()
        stock_code = str(stock_code or "").strip()
        narrative_id = str(narrative_id or "").strip()
        for pack in _list(self.evidence_packs().get("packs")):
            for mapping in _list(pack.get("proposed_mappings")):
                if evidence_pack_id and mapping.get("evidence_pack_id") != evidence_pack_id:
                    continue
                if not evidence_pack_id and (
                    str(pack.get("stock_code") or "") != stock_code
                    or str(mapping.get("narrative_id") or "") != narrative_id
                ):
                    continue
                return _evidence_pack_detail_payload(
                    pack=pack,
                    mapping=mapping,
                )
        return None

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

    def promotion_decisions(self) -> dict[str, Any]:
        path = self.config.promotion_decisions_path
        if not path.exists():
            return {"version": PROMOTION_DECISION_LEDGER_VERSION, "items": []}
        return _load_object(path, label="promotion decisions")

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

    def candidate_detail(self, candidate_id: str) -> dict[str, Any] | None:
        candidate_id = str(candidate_id or "").strip()
        candidate = _candidate_by_id(self.candidates(), candidate_id)
        if candidate is None:
            return None
        review_history = _review_actions_for_candidate(
            self.review_actions(),
            candidate_id,
        )
        latest_action = review_history[-1] if review_history else {}
        gates = _promotion_gates(candidate=candidate, latest_action=latest_action)
        missing_gates = [
            gate["gate_id"] for gate in gates if gate["status"] != "passed"
        ]
        status, recommended_action = _review_status(
            latest_action=latest_action,
            missing_gates=missing_gates,
        )
        return {
            "version": "candidate-narrative-detail-v1",
            "candidate_narrative_id": candidate_id,
            "candidate": candidate,
            "trust_status": str(candidate.get("trust_status") or "candidate_untrusted"),
            "latest_review_action": latest_action,
            "review_history": review_history,
            "promotion_preflight": {
                "result": "blocked" if missing_gates else "ready_for_trust_audit",
                "missing_gates": missing_gates,
                "gates": gates,
                "latest_review_action": latest_action,
                "promotion_effect": "none",
                "trust_status_after_preflight": "candidate_untrusted",
            },
            "missing_gates": missing_gates,
            "review_status": status,
            "recommended_action": recommended_action,
            "source_evidence_refs": _source_evidence_refs(candidate),
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
        summary = {
            "narrative_count": len(_list(registry.get("narratives"))),
            "candidate_narrative_count": len(
                _list(candidates.get("candidate_narratives"))
            ),
            "stock_mapping_count": len(_list(mappings.get("mappings"))),
            "evidence_pack_count": len(_list(evidence.get("packs"))),
            "review_action_count": len(_list(review_actions.get("items"))),
        }
        return {
            "version": "narrative-service-ops-summary-v0",
            "generated_at": _now(),
            "summary": summary,
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
            "diagnostics": operational_diagnostics(
                config=self.config,
                status="available",
                queue_summary=review_queue["summary"],
                audit_status=str(trust_audit["result"]),
                product_data_gaps=_product_data_gaps(summary),
            ),
        }

    def radar_contract(self) -> dict[str, Any]:
        return radar_contract(self.config)

    def radar_signals(self) -> dict[str, Any]:
        return radar_source_signals(_all_events(self))

    def radar_mined_candidates(self) -> dict[str, Any]:
        return radar_mined_candidates(_all_events(self))

    def radar_scores(
        self,
        *,
        as_of: str = "",
        window_days: Any = "",
        baseline_days: Any = "",
        half_life_hours: Any = "",
    ) -> dict[str, Any]:
        return radar_scores(
            events=_all_events(self),
            config=self.config,
            as_of=as_of,
            window_days=window_days,
            baseline_days=baseline_days,
            half_life_hours=half_life_hours,
        )

    def radar_bubbles(
        self,
        *,
        as_of: str = "",
        window_days: Any = "",
        baseline_days: Any = "",
        half_life_hours: Any = "",
    ) -> dict[str, Any]:
        return radar_bubbles(
            events=_all_events(self),
            config=self.config,
            as_of=as_of,
            window_days=window_days,
            baseline_days=baseline_days,
            half_life_hours=half_life_hours,
        )

    def radar_evidence_detail(
        self,
        *,
        narrative_id: str,
        as_of: str = "",
        window_days: Any = "",
        baseline_days: Any = "",
        half_life_hours: Any = "",
    ) -> dict[str, Any]:
        return radar_evidence_detail(
            events=_all_events(self),
            review_actions=self.review_actions(),
            config=self.config,
            narrative_id=narrative_id,
            as_of=as_of,
            window_days=window_days,
            baseline_days=baseline_days,
            half_life_hours=half_life_hours,
        )

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
        reinforcements = _evidence_reinforcements_from_events(normalized)
        return {
            "ingested_event_count": len(normalized),
            "dry_run": dry_run,
            "candidate_narratives": candidates,
            "evidence_reinforcements": reinforcements,
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

    def commit_promotion(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(payload.get("candidate_narrative_id") or "").strip()
        target_narrative_id = str(payload.get("target_narrative_id") or "").strip()
        review_action_id = str(payload.get("review_action_id") or "").strip()
        trust_audit_id = str(payload.get("trust_audit_id") or "").strip()
        trust_audit_result = str(payload.get("trust_audit_result") or "").strip()
        promoted_by = str(payload.get("promoted_by") or "").strip()
        promotion_note = str(payload.get("promotion_note") or "").strip()
        target_stock_codes = _strings(payload.get("target_stock_codes"))
        if not candidate_id:
            raise ValueError("candidate_narrative_id is required")
        if not target_narrative_id:
            raise ValueError("target_narrative_id is required")
        if not review_action_id:
            raise ValueError("review_action_id is required")
        if not trust_audit_id:
            raise ValueError("trust_audit_id is required")
        if not promoted_by:
            raise ValueError("promoted_by is required")
        if not promotion_note:
            raise ValueError("promotion_note is required")
        if not target_stock_codes:
            raise ValueError("target_stock_codes must contain at least one stock code")
        candidate = _candidate_by_id(self.candidates(), candidate_id)
        if candidate is None:
            raise ValueError(f"Unknown candidate_narrative_id: {candidate_id}")
        latest_action = _latest_actions_by_candidate(self.review_actions()).get(
            candidate_id,
            {},
        )
        missing_gates = _promotion_commit_missing_gates(
            candidate=candidate,
            latest_action=latest_action,
            review_action_id=review_action_id,
            trust_audit_result=trust_audit_result,
        )
        if missing_gates:
            raise PromotionGateError(
                candidate_id=candidate_id,
                missing_gates=missing_gates,
            )
        decisions = self.promotion_decisions()
        existing_decisions = _list(decisions.get("items"))
        promotion_decision_id, identity_metadata = promotion_decision_identity(
            candidate_narrative_id=candidate_id,
            target_narrative_id=target_narrative_id,
            review_action_id=review_action_id,
        )
        existing_decision = _promotion_decision_by_id(
            existing_decisions,
            promotion_decision_id,
        )
        if existing_decision is not None:
            return {"decision": {**existing_decision, "idempotent_replay": True}}
        promoted_at = _now()
        decision = {
            "schema_version": "promotion-decision-ledger-record-v1",
            "ledger_record_type": "promotion_decision",
            "ledger_sequence": len(existing_decisions) + 1,
            "recorded_at": promoted_at,
            "promotion_decision_id": promotion_decision_id,
            "candidate_narrative_id": candidate_id,
            "target_narrative_id": target_narrative_id,
            "review_action_id": review_action_id,
            "trust_audit_id": trust_audit_id,
            "trust_audit_result": trust_audit_result,
            "promoted_by": promoted_by,
            "promoted_at": promoted_at,
            "promotion_note": promotion_note,
            "identity_metadata": identity_metadata,
            "source_metadata": _mapping(payload.get("source_metadata")),
            "trust_status_before": "candidate_untrusted",
            "trust_status_after": "trusted_validated",
            "promotion_effect": "trusted_validated",
            "atomic_write_set": [*PROMOTION_ATOMIC_WRITE_SET],
            "rollback_plan": "restore_pre_transaction_json_snapshots",
            "target_stock_codes": target_stock_codes,
        }
        registry = _registry_with_promotion(
            self.registry(),
            candidate=candidate,
            decision=decision,
        )
        mappings = _mappings_with_promotion(
            self.mappings(),
            candidate=candidate,
            decision=decision,
        )
        evidence = _evidence_with_promotion(
            _load_object(self.config.evidence_packs_path, label="evidence packs"),
            candidate=candidate,
            decision=decision,
        )
        decisions = {
            **decisions,
            "version": PROMOTION_DECISION_LEDGER_VERSION,
            "items": [*existing_decisions, decision],
        }
        _write_promotion_transaction(
            registry_path=self.config.registry_path,
            registry=registry,
            mappings_path=self.config.mappings_path,
            mappings=mappings,
            evidence_packs_path=self.config.evidence_packs_path,
            evidence=evidence,
            promotion_decisions_path=self.config.promotion_decisions_path,
            decisions=decisions,
        )
        return {"decision": decision}


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


def _review_actions_for_candidate(
    payload: dict[str, Any],
    candidate_id: str,
) -> list[dict[str, Any]]:
    return [
        item
        for item in _list(payload.get("items"))
        if str(item.get("candidate_narrative_id") or "") == candidate_id
    ]


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


def _promotion_commit_missing_gates(
    *,
    candidate: dict[str, Any],
    latest_action: dict[str, Any],
    review_action_id: str,
    trust_audit_result: str,
) -> list[str]:
    missing = [
        gate["gate_id"]
        for gate in _promotion_gates(candidate=candidate, latest_action=latest_action)
        if gate["status"] != "passed"
    ]
    if str(latest_action.get("review_action_id") or "") != review_action_id:
        missing = [*missing, "service_review_approval"]
    if trust_audit_result != "passed":
        missing = [*missing, "trust_audit_pass"]
    return sorted(set(missing))


def _promotion_decision_by_id(
    decisions: list[dict[str, Any]],
    promotion_decision_id: str,
) -> dict[str, Any] | None:
    for item in decisions:
        if str(item.get("promotion_decision_id") or "") == promotion_decision_id:
            return item
    return None


def _registry_with_promotion(
    registry: dict[str, Any],
    *,
    candidate: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    target_narrative_id = str(decision["target_narrative_id"])
    promoted_record = {
        "narrative_id": target_narrative_id,
        "name": str(candidate.get("name") or target_narrative_id),
        "trust_status": "trusted_validated",
        "source_candidate_narrative_id": str(decision["candidate_narrative_id"]),
        "promotion_decision_id": str(decision["promotion_decision_id"]),
        "review_action_id": str(decision["review_action_id"]),
        "trusted_at": str(decision["promoted_at"]),
    }
    existing = [
        item
        for item in _list(registry.get("narratives"))
        if str(item.get("narrative_id") or "") != target_narrative_id
    ]
    return {**registry, "narratives": [*existing, promoted_record]}


def _mappings_with_promotion(
    mappings: dict[str, Any],
    *,
    candidate: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    target_narrative_id = str(decision["target_narrative_id"])
    target_stock_codes = _strings(decision.get("target_stock_codes"))
    existing = [
        item
        for item in _list(mappings.get("mappings"))
        if (
            str(item.get("narrative_id") or "") != target_narrative_id
            or str(item.get("stock_code") or "") not in set(target_stock_codes)
        )
    ]
    promoted = [
        {
            "stock_code": stock_code,
            "narrative_id": target_narrative_id,
            "narrative_name": str(candidate.get("name") or target_narrative_id),
            "confidence": _float(candidate.get("confidence")),
            "method": "trusted_promotion",
            "trust_status": "trusted_validated",
            "source_trust_status": "trusted_validated",
            "source_candidate_narrative_id": str(decision["candidate_narrative_id"]),
            "promotion_decision_id": str(decision["promotion_decision_id"]),
            "review_action_id": str(decision["review_action_id"]),
        }
        for stock_code in target_stock_codes
    ]
    return {**mappings, "mappings": [*existing, *promoted]}


def _evidence_with_promotion(
    evidence: dict[str, Any],
    *,
    candidate: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    target_narrative_id = str(decision["target_narrative_id"])
    target_stock_codes = _strings(decision.get("target_stock_codes"))
    remaining_stock_codes = set(target_stock_codes)
    packs = []
    for pack in _list(evidence.get("packs")):
        stock_code = str(pack.get("stock_code") or "")
        if stock_code not in remaining_stock_codes:
            packs.append(pack)
            continue
        remaining_stock_codes.remove(stock_code)
        existing_mappings = [
            item
            for item in _list(pack.get("proposed_mappings"))
            if str(item.get("narrative_id") or "") != target_narrative_id
        ]
        packs.append(
            {
                **pack,
                "proposed_mappings": [
                    *existing_mappings,
                    _promotion_evidence_mapping(
                        candidate=candidate,
                        decision=decision,
                    ),
                ],
            }
        )
    for stock_code in sorted(remaining_stock_codes):
        packs.append(
            {
                "stock_code": stock_code,
                "stock_name": "",
                "trust_status": "trusted_validated",
                "proposed_mappings": [
                    _promotion_evidence_mapping(
                        candidate=candidate,
                        decision=decision,
                    )
                ],
            }
        )
    return {**evidence, "packs": packs}


def _promotion_evidence_mapping(
    *,
    candidate: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    target_narrative_id = str(decision["target_narrative_id"])
    return {
        "narrative_id": target_narrative_id,
        "narrative_name": str(candidate.get("name") or target_narrative_id),
        "trust_status": "trusted_validated",
        "mapping_rationale": str(candidate.get("rationale") or ""),
        "exclusion_rationale": _strings(candidate.get("exclusion_criteria"))
        or _strings(candidate.get("exclusion_criteria_zh")),
        "confidence_components": {
            "candidate_confidence": _float(candidate.get("confidence")),
        },
        "evidence_items": _promotion_evidence_items(candidate),
        "source_candidate_narrative_id": str(decision["candidate_narrative_id"]),
        "promotion_decision_id": str(decision["promotion_decision_id"]),
    }


def _promotion_evidence_items(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    citation_ids = _strings(candidate.get("representative_citation_ids"))
    citations = _list(candidate.get("representative_citations"))
    if citations:
        return citations
    return [
        {
            "source_name": citation_id,
            "source_url": "",
            "source_type": "candidate_citation",
            "evidence_summary": f"Candidate citation {citation_id}",
            "supports": ["source_evidence"],
        }
        for citation_id in citation_ids
    ]


def _write_promotion_transaction(
    *,
    registry_path: Path,
    registry: dict[str, Any],
    mappings_path: Path,
    mappings: dict[str, Any],
    evidence_packs_path: Path,
    evidence: dict[str, Any],
    promotion_decisions_path: Path,
    decisions: dict[str, Any],
) -> None:
    paths = [
        registry_path,
        mappings_path,
        evidence_packs_path,
        promotion_decisions_path,
    ]
    snapshots = {
        path: path.read_text(encoding="utf-8") if path.exists() else None
        for path in paths
    }
    try:
        _write_object(registry_path, registry)
        _write_object(mappings_path, mappings)
        _write_object(evidence_packs_path, evidence)
        _write_object(promotion_decisions_path, decisions)
    except Exception:
        _restore_snapshots(snapshots)
        raise


def _restore_snapshots(snapshots: dict[Path, str | None]) -> None:
    for path, text in snapshots.items():
        if text is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


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


def _product_data_gaps(summary: dict[str, int]) -> list[dict[str, str]]:
    gap_definitions = [
        (
            "narrative_count",
            "NARRATIVES_EMPTY",
            "No narratives are currently available.",
            "narratives",
        ),
        (
            "stock_mapping_count",
            "STOCK_MAPPINGS_EMPTY",
            "No stock mappings are currently available.",
            "stock_mappings",
        ),
        (
            "evidence_pack_count",
            "EVIDENCE_PACKS_EMPTY",
            "No evidence packs are currently available.",
            "evidence_packs",
        ),
        (
            "candidate_narrative_count",
            "CANDIDATE_NARRATIVES_EMPTY",
            "No candidate narratives are currently available.",
            "candidate_narratives",
        ),
    ]
    return [
        {"code": code, "message": message, "scope": scope}
        for field, code, message, scope in gap_definitions
        if summary.get(field, 0) == 0
    ]


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
    source_type = _normalize_source_type(event.get("source_type"))
    event_id, identity_metadata = source_event_identity(
        {**dict(event), "source_type": source_type}
    )
    normalized = {
        **dict(event),
        "event_id": event_id,
        "identity_metadata": identity_metadata,
        "source_type": source_type,
        "event_time": str(event.get("event_time") or _now()),
        "source_metadata": _source_metadata(event, source_type),
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


def _evidence_reinforcements_from_events(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reinforcements = []
    for event in events:
        source_event_id = str(event.get("event_id") or "")
        for narrative_id in _strings(event.get("reinforces_narrative_ids")):
            if not narrative_id:
                continue
            reinforcements.append(
                {
                    "evidence_reinforcement_id": stable_id(
                        "ERF",
                        [source_event_id, narrative_id],
                    ),
                    "source_event_id": source_event_id,
                    "narrative_id": narrative_id,
                    "trust_status": "candidate_untrusted",
                    "promotion_effect": "none",
                    "source_metadata": _mapping(event.get("source_metadata")),
                    "supported_claim_types": _strings(
                        event.get("supported_claim_types")
                    )
                    or _strings(event.get("supports")),
                    "evidence_summary": str(
                        event.get("summary") or event.get("title") or ""
                    ),
                }
            )
    return reinforcements


def _normalize_source_type(value: Any) -> str:
    source_type = str(value or "manual").strip()
    if source_type == "social":
        return "social_future"
    return source_type or "manual"


def _source_metadata(event: dict[str, Any], source_type: str) -> dict[str, Any]:
    metadata = dict(_mapping(event.get("source_metadata")))
    for key in (
        "provider",
        "provider_version",
        "permission_status",
        "degradation_state",
        "source_name",
        "source_url",
    ):
        value = event.get(key)
        if value not in (None, ""):
            metadata[key] = str(value)
    if "permission_status" not in metadata and metadata.get("permission"):
        metadata["permission_status"] = str(metadata["permission"])
    provider_preference = _provider_preference(source_type, metadata)
    metadata.setdefault("provider", provider_preference[0])
    metadata.setdefault("provider_version", "unknown")
    metadata.setdefault("permission_status", "not_declared")
    metadata.setdefault("degradation_state", "unknown")
    metadata.setdefault("source_url", str(event.get("source_url") or ""))
    metadata.setdefault("source_name", str(event.get("source_name") or ""))
    metadata["source_type"] = source_type
    metadata["provider_preference"] = provider_preference
    metadata["source_mode"] = SOURCE_MODE_BY_SOURCE_TYPE.get(
        source_type,
        "unsupported_source_type_recorded_without_promotion",
    )
    return metadata


def _provider_preference(
    source_type: str,
    metadata: dict[str, Any],
) -> list[str]:
    configured = PROVIDER_PREFERENCE_BY_SOURCE_TYPE.get(source_type)
    if configured:
        return [*configured]
    provider = str(metadata.get("provider") or "unknown_provider")
    return [provider]


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


def _evidence_pack_detail_payload(
    *,
    pack: dict[str, Any],
    mapping: dict[str, Any],
) -> dict[str, Any]:
    stock_code = str(pack.get("stock_code") or "")
    narrative_id = str(mapping.get("narrative_id") or "")
    evidence_pack_id = str(mapping.get("evidence_pack_id") or "")
    return {
        "version": "mapping-evidence-pack-detail-v1",
        "lookup": {
            "evidence_pack_id": evidence_pack_id,
            "stock_code": stock_code,
            "narrative_id": narrative_id,
        },
        "evidence_pack_id": evidence_pack_id,
        "candidate_mapping_id": str(mapping.get("candidate_mapping_id") or ""),
        "stock_code": stock_code,
        "stock_name": str(pack.get("stock_name") or ""),
        "narrative_id": narrative_id,
        "narrative_name": str(mapping.get("narrative_name") or ""),
        "trust_status": str(mapping.get("trust_status") or "candidate_untrusted"),
        "mapping_rationale": str(mapping.get("mapping_rationale") or ""),
        "exclusion_rationale": _strings(mapping.get("exclusion_rationale")),
        "confidence_components": _mapping(mapping.get("confidence_components")),
        "evidence_items": [
            _evidence_item_payload(item)
            for item in _list(mapping.get("evidence_items"))
        ],
        "promotion_effect": "none",
        "recommended_action": "human_review",
    }


def _evidence_item_payload(item: dict[str, Any]) -> dict[str, Any]:
    supports = _strings(item.get("supports"))
    return {
        "source_name": str(item.get("source_name") or ""),
        "source_url": str(item.get("source_url") or ""),
        "source_type": str(item.get("source_type") or ""),
        "evidence_date": str(item.get("evidence_date") or ""),
        "evidence_summary": str(item.get("evidence_summary") or ""),
        "supports": supports,
        "supported_claim_types": supports,
    }


def _source_evidence_refs(candidate: dict[str, Any]) -> dict[str, Any]:
    derivation = _mapping(candidate.get("derivation"))
    return {
        "source_event_ids": _strings(candidate.get("source_event_ids")),
        "representative_citation_ids": _strings(
            candidate.get("representative_citation_ids")
        ),
        "representative_citations": _list(candidate.get("representative_citations")),
        "supporting_source_item_ids": _strings(
            derivation.get("supporting_source_item_ids")
        ),
    }


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


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
