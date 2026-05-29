from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from html import escape
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
    radar_preview,
    radar_scores,
    radar_source_signals,
    radar_ui_contract,
    render_radar_ui,
)

INTAKE_LEDGER_VERSION = "service-intake-events-v1"
REVIEW_ACTION_LEDGER_VERSION = "narrative-review-actions-v1"
PROMOTION_DECISION_LEDGER_VERSION = "narrative-promotion-decisions-v1"
JOB_DEFINITIONS_VERSION = "narrative-job-definitions-v1"
JOB_RUN_LEDGER_VERSION = "narrative-job-runs-v1"
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
REVIEW_WORKFLOW_STATES = [
    "candidate_untrusted",
    "pending_review",
    "approved_blocked_by_evidence",
    "ready_for_trust_audit",
    "trusted_validated",
    "rejected",
    "deferred",
    "deprecated",
]
JOB_RUN_STATUSES = ["queued", "running", "success", "degraded", "failed"]


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

    def job_definitions(self) -> dict[str, Any]:
        path = self.config.job_definitions_path
        if not path.exists():
            return _default_job_definitions()
        return _load_object(path, label="job definitions")

    def job_run_ledger(self) -> dict[str, Any]:
        path = self.config.job_runs_path
        if not path.exists():
            return {"version": JOB_RUN_LEDGER_VERSION, "items": []}
        return _load_object(path, label="job run ledger")

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

    def radar_ui_contract(self) -> dict[str, Any]:
        return radar_ui_contract()

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
        include_explanation: bool = False,
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
            include_explanation=include_explanation,
        )

    def radar_preview(
        self,
        *,
        as_of: str = "",
        window_days: Any = "",
        baseline_days: Any = "",
        half_life_hours: Any = "",
    ) -> dict[str, Any]:
        return radar_preview(
            events=_all_events(self),
            config=self.config,
            as_of=as_of,
            window_days=window_days,
            baseline_days=baseline_days,
            half_life_hours=half_life_hours,
        )

    def radar_ui_html(
        self,
        *,
        as_of: str = "",
        window_days: Any = "",
        baseline_days: Any = "",
        half_life_hours: Any = "",
    ) -> str:
        return render_radar_ui(
            bubbles_payload=self.radar_bubbles(
                as_of=as_of,
                window_days=window_days,
                baseline_days=baseline_days,
                half_life_hours=half_life_hours,
            ),
            ui_contract=self.radar_ui_contract(),
            generated_at=_now(),
        )

    def review_workflow_contract(self) -> dict[str, Any]:
        return {
            "version": "narrative-review-workflow-contract-v1",
            "states": [*REVIEW_WORKFLOW_STATES],
            "rules": {
                "intake": "creates candidate_untrusted records only",
                "review_action": "approve/reject/defer only; cannot promote directly",
                "preflight": "non_mutating",
                "promotion_commit": "only trusted-record write path",
                "failed_promotion": "writes no trusted records",
            },
            "transitions": {
                "candidate_untrusted": {
                    "intake": "pending_review",
                },
                "pending_review": {
                    "approve": [
                        "approved_blocked_by_evidence",
                        "ready_for_trust_audit",
                    ],
                    "reject": "rejected",
                    "defer": "deferred",
                },
                "approved_blocked_by_evidence": {
                    "complete_evidence_gates": "ready_for_trust_audit",
                },
                "ready_for_trust_audit": {
                    "promotion_commit": "trusted_validated",
                },
                "trusted_validated": {
                    "deprecate": "deprecated",
                },
            },
            "audit_fields": [
                "reviewed_by",
                "action",
                "reviewed_at",
                "review_note",
                "promotion_decision_id",
            ],
        }

    def review_workflow_summary(self, *, status: str = "") -> dict[str, Any]:
        candidates = self.candidates()["candidate_narratives"]
        latest_actions = _latest_actions_by_candidate(self.review_actions())
        promotion_decisions = _latest_promotions_by_candidate(self.promotion_decisions())
        items = [
            _review_workflow_item(
                candidate=candidate,
                latest_action=latest_actions.get(
                    candidate["candidate_narrative_id"],
                    {},
                ),
                promotion_decision=promotion_decisions.get(
                    candidate["candidate_narrative_id"],
                    {},
                ),
            )
            for candidate in candidates
        ]
        if status:
            items = [item for item in items if item["workflow_state"] == status]
        return {
            "version": "narrative-review-workflow-v1",
            "generated_at": _now(),
            "contract_version": self.review_workflow_contract()["version"],
            "filter": {"status": status},
            "summary": _workflow_summary(items),
            "items": items,
        }

    def review_workflow_html(self, *, status: str = "") -> str:
        payload = self.review_workflow_summary(status=status)
        rows = "\n".join(
            _render_review_workflow_row(item)
            for item in _list(payload.get("items"))
        )
        if not rows:
            rows = (
                '<tr><td colspan="5">No review workflow items match this filter.</td>'
                "</tr>"
            )
        summary = _mapping(payload.get("summary"))
        summary_markup = "".join(
            f'<span><strong>{_html(key)}</strong> {_html(value)}</span>'
            for key, value in summary.items()
        )
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8" />',
                '<meta name="viewport" content="width=device-width, initial-scale=1" />',
                "<title>Narrative Review Workflow</title>",
                "<style>",
                "body{margin:0;background:#f5f7fa;color:#1e252c;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}",
                "main{max-width:1120px;margin:0 auto;padding:24px}",
                "header{border-bottom:1px solid #d9e0e8;padding-bottom:16px}",
                "h1{font-size:28px;margin:0 0 8px}",
                "p{margin:0;color:#5d6b7a}",
                ".summary{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}",
                ".summary span{border:1px solid #d9e0e8;background:#fff;padding:8px 10px}",
                "table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9e0e8}",
                "th,td{text-align:left;border-bottom:1px solid #e4e9ef;padding:10px;vertical-align:top}",
                "th{font-size:12px;text-transform:uppercase;color:#5d6b7a;background:#edf2f7}",
                "code{background:#edf2f7;padding:2px 5px}",
                ".guardrails{margin-top:16px;color:#45515f}",
                "</style>",
                "</head>",
                "<body>",
                "<main>",
                "<header>",
                "<h1>Narrative Review Workflow</h1>",
                (
                    "<p>Human review, promotion preflight, and trusted promotion "
                    "state surface for candidate narratives.</p>"
                ),
                "</header>",
                f'<section class="summary">{summary_markup}</section>',
                "<table>",
                "<thead><tr><th>Candidate</th><th>State</th><th>Preflight</th>"
                "<th>Review Action</th><th>Promotion</th></tr></thead>",
                f"<tbody>{rows}</tbody>",
                "</table>",
                (
                    '<p class="guardrails">promotion preflight is non-mutating; '
                    "promotion commit is the only trusted-record write path.</p>"
                ),
                "</main>",
                "</body>",
                "</html>",
            ]
        )

    def scheduling_contract(self) -> dict[str, Any]:
        return {
            "version": "narrative-scheduling-contract-v1",
            "job_definition_fields": [
                "job_id",
                "job_type",
                "enabled",
                "schedule",
                "parameters",
                "owner_service",
                "timeout_seconds",
                "concurrency_guard",
                "retry_policy",
                "idempotency_key",
            ],
            "run_ledger_fields": [
                "run_id",
                "job_id",
                "triggered_by",
                "started_at",
                "finished_at",
                "status",
                "duration_ms",
                "warnings",
                "artifacts",
                "error_category",
                "idempotency_key",
            ],
            "statuses": [*JOB_RUN_STATUSES],
            "write_safety": {
                "source_intake": "dry_run_by_default",
                "radar_scoring": "read_only_snapshot",
                "live_provider_smoke": "diagnostic_only",
                "report_pack_generation": "artifact_only",
                "trusted_store_mutation": "forbidden",
            },
            "manual_run_endpoint": "/api/v1/narratives/jobs/run",
            "definitions_endpoint": "/api/v1/narratives/jobs/definitions",
            "run_ledger_endpoint": "/api/v1/narratives/jobs/runs",
        }

    def job_runs(self, *, job_id: str = "", status: str = "") -> dict[str, Any]:
        items = _list(self.job_run_ledger().get("items"))
        if job_id:
            items = [item for item in items if str(item.get("job_id") or "") == job_id]
        if status:
            items = [item for item in items if str(item.get("status") or "") == status]
        return {
            "version": JOB_RUN_LEDGER_VERSION,
            "filter": {"job_id": job_id, "status": status},
            "summary": _job_run_summary(items),
            "items": items,
        }

    def run_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = str(payload.get("job_id") or "").strip()
        triggered_by = str(payload.get("triggered_by") or "manual").strip() or "manual"
        idempotency_key = str(payload.get("idempotency_key") or "").strip()
        request_parameters = _mapping(payload.get("parameters"))
        if not job_id:
            raise ValueError("job_id is required")
        definitions = self.job_definitions()
        job = _job_definition_by_id(definitions, job_id)
        if not job:
            raise ValueError(f"Unknown job_id: {job_id}")
        if not bool(job.get("enabled", True)):
            raise ValueError(f"Job is disabled: {job_id}")
        ledger = self.job_run_ledger()
        existing_runs = _list(ledger.get("items"))
        existing = _job_run_by_idempotency_key(
            existing_runs,
            job_id=job_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return {"run": {**existing, "idempotent_replay": True}}
        started_at = _now()
        run = _execute_job_definition(
            store=self,
            job=job,
            triggered_by=triggered_by,
            idempotency_key=idempotency_key,
            request_parameters=request_parameters,
            started_at=started_at,
        )
        ledger = {
            **ledger,
            "version": JOB_RUN_LEDGER_VERSION,
            "items": [*existing_runs, run],
        }
        _write_object(self.config.job_runs_path, ledger)
        return {"run": run}

    def storage_migration_plan(self) -> dict[str, Any]:
        return {
            "version": "narrative-durable-storage-migration-plan-v1",
            "current_store": "json_file_ledgers_v1",
            "target_adapters": ["sqlite_local", "postgres_managed"],
            "entities": _durable_storage_entities(),
            "contract_invariants": {
                "http_contract_change_allowed": False,
                "append_only_semantics_preserved": True,
                "json_mode_remains_available": True,
                "trusted_promotion_write_path": "promotion_commit_only",
            },
            "migration_phases": [
                "backup_json_ledgers",
                "create_schema",
                "backfill_append_only_ledgers",
                "backfill_read_models",
                "run_http_parity_checks",
                "enable_sqlite_adapter",
                "retain_json_fallback_until_parity_passes",
            ],
            "parity_check_endpoints": [
                "/api/v1/narratives/registry",
                "/api/v1/narratives/mappings",
                "/api/v1/narratives/evidence-packs",
                "/api/v1/narratives/candidates",
                "/api/v1/narratives/review-queue",
                "/api/v1/narratives/review-actions",
                "/api/v1/narratives/promotion/preflight",
                "/api/v1/narratives/radar/preview",
                "/api/v1/narratives/jobs/runs",
            ],
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


def _default_job_definitions() -> dict[str, Any]:
    return {
        "version": JOB_DEFINITIONS_VERSION,
        "jobs": [
            _job_definition(
                job_id="live-provider-smoke",
                job_type="live_provider_smoke",
                schedule={"mode": "manual", "recommended": "before_release"},
                parameters={"output_scope": "credential_safe_diagnostics"},
            ),
            _job_definition(
                job_id="source-intake",
                job_type="source_intake",
                schedule={"mode": "manual_or_scheduled", "cadence": "hourly"},
                parameters={"dry_run": True},
            ),
            _job_definition(
                job_id="narrative-radar-scoring",
                job_type="radar_scoring",
                schedule={"mode": "manual_or_scheduled", "cadence": "hourly"},
                parameters={"window_days": 7, "baseline_days": 30},
            ),
            _job_definition(
                job_id="report-pack-generation",
                job_type="report_pack_generation",
                schedule={"mode": "manual_or_scheduled", "cadence": "daily"},
                parameters={"artifact_only": True},
            ),
        ],
    }


def _job_definition(
    *,
    job_id: str,
    job_type: str,
    schedule: dict[str, Any],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "job_type": job_type,
        "enabled": True,
        "schedule": schedule,
        "parameters": parameters,
        "owner_service": "stock-narrative-service",
        "timeout_seconds": 300,
        "concurrency_guard": "single_active_run_per_job",
        "retry_policy": {"max_attempts": 1, "backoff": "none"},
        "idempotency_key": "required_for_scheduled_runs",
    }


def _job_definition_by_id(
    definitions: dict[str, Any],
    job_id: str,
) -> dict[str, Any]:
    for item in _list(definitions.get("jobs")):
        if str(item.get("job_id") or "") == job_id:
            return item
    return {}


def _job_run_by_idempotency_key(
    runs: list[dict[str, Any]],
    *,
    job_id: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    if not idempotency_key:
        return None
    for item in runs:
        if (
            str(item.get("job_id") or "") == job_id
            and str(item.get("idempotency_key") or "") == idempotency_key
        ):
            return item
    return None


def _execute_job_definition(
    *,
    store: NarrativeStore,
    job: dict[str, Any],
    triggered_by: str,
    idempotency_key: str,
    request_parameters: dict[str, Any],
    started_at: str,
) -> dict[str, Any]:
    job_id = str(job.get("job_id") or "")
    job_type = str(job.get("job_type") or "")
    parameters = {**_mapping(job.get("parameters")), **request_parameters}
    run_id = stable_id("JR", [job_id, idempotency_key or started_at])
    try:
        execution = _job_execution_result(
            store=store,
            job_type=job_type,
            parameters=parameters,
        )
    except Exception as exc:  # pragma: no cover - defensive run ledger capture
        execution = {
            "status": "failed",
            "warnings": [
                {
                    "code": "JOB_EXECUTION_FAILED",
                    "message": str(exc),
                    "classification": "system_failure",
                }
            ],
            "artifacts": [],
            "error_category": "runtime_error",
        }
    finished_at = _now()
    return {
        "schema_version": "narrative-job-run-record-v1",
        "ledger_record_type": "job_run",
        "run_id": run_id,
        "job_id": job_id,
        "job_type": job_type,
        "owner_service": str(job.get("owner_service") or "stock-narrative-service"),
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": str(execution["status"]),
        "duration_ms": _duration_ms(started_at, finished_at),
        "warnings": _list(execution.get("warnings")),
        "artifacts": _list(execution.get("artifacts")),
        "error_category": str(execution.get("error_category") or ""),
        "idempotency_key": idempotency_key,
        "timeout_seconds": int(job.get("timeout_seconds") or 0),
        "concurrency_guard": str(
            job.get("concurrency_guard") or "single_active_run_per_job"
        ),
        "retry_policy": _mapping(job.get("retry_policy")),
        "parameters": parameters,
        "trusted_store_mutation": "none",
    }


def _job_execution_result(
    *,
    store: NarrativeStore,
    job_type: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if job_type == "radar_scoring":
        preview = store.radar_preview(
            window_days=parameters.get("window_days", ""),
            baseline_days=parameters.get("baseline_days", ""),
        )
        warnings = _list(preview.get("degradation_warnings"))
        return {
            "status": "degraded" if warnings else "success",
            "warnings": warnings,
            "artifacts": [
                {
                    "label": "radar_preview",
                    "path": "/api/v1/narratives/radar/preview",
                }
            ],
            "error_category": "",
        }
    if job_type == "source_intake":
        return {
            "status": "success",
            "warnings": [],
            "artifacts": [
                {
                    "label": "review_queue",
                    "path": "/api/v1/narratives/review-queue",
                }
            ],
            "error_category": "",
        }
    if job_type == "live_provider_smoke":
        return {
            "status": "degraded",
            "warnings": [
                {
                    "code": "LIVE_SMOKE_EXTERNAL_COMMAND",
                    "message": (
                        "Run scripts/run_live_validation_dashboard.py for live "
                        "credential checks."
                    ),
                    "classification": "operational_action_required",
                }
            ],
            "artifacts": [
                {
                    "label": "live_validation_dashboard",
                    "path": "outputs/live_validation_dashboard/",
                }
            ],
            "error_category": "manual_validation_required",
        }
    if job_type == "report_pack_generation":
        return {
            "status": "degraded",
            "warnings": [
                {
                    "code": "REPORT_PACK_EXTERNAL_COMMAND",
                    "message": (
                        "Report-pack generation remains an FNI artifact command."
                    ),
                    "classification": "operational_action_required",
                }
            ],
            "artifacts": [
                {
                    "label": "reviewable_fund_report_pack",
                    "path": "scripts/run_reviewable_fund_report_pack.py",
                }
            ],
            "error_category": "external_artifact_command",
        }
    return {
        "status": "failed",
        "warnings": [
            {
                "code": "JOB_TYPE_UNSUPPORTED",
                "message": f"Unsupported job_type: {job_type}",
                "classification": "invalid_configuration",
            }
        ],
        "artifacts": [],
        "error_category": "unsupported_job_type",
    }


def _job_run_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {status: 0 for status in JOB_RUN_STATUSES}
    for item in items:
        status = str(item.get("status") or "")
        summary[status] = summary.get(status, 0) + 1
    return summary


def _durable_storage_entities() -> list[dict[str, Any]]:
    return [
        _entity(
            name="narratives",
            primary_key="narrative_id",
            write_model="trusted_read_model",
            idempotency="narrative_id",
            source="reviewed_registry_or_promotion_commit",
        ),
        _entity(
            name="stock_narrative_mappings",
            primary_key="stock_code_narrative_id",
            write_model="trusted_read_model",
            idempotency="stock_code_narrative_id",
            source="reviewed_mappings_or_promotion_commit",
        ),
        _entity(
            name="evidence_packs",
            primary_key="evidence_pack_id",
            write_model="trusted_read_model",
            idempotency="stock_code_narrative_id",
            source="mapping_evidence_packs_or_promotion_commit",
        ),
        _entity(
            name="source_events",
            primary_key="event_id",
            write_model="append_only",
            idempotency="source_event_identity",
            source="candidate_intake_events",
        ),
        _entity(
            name="candidate_narratives",
            primary_key="candidate_narrative_id",
            write_model="derived_read_model",
            idempotency="candidate_narrative_identity",
            source="source_events",
        ),
        _entity(
            name="review_actions",
            primary_key="review_action_id",
            write_model="append_only",
            idempotency="candidate_action_reviewer_idempotency_key",
            source="review_actions",
        ),
        _entity(
            name="promotion_decisions",
            primary_key="promotion_decision_id",
            write_model="append_only",
            idempotency="candidate_target_review_action",
            source="promotion_decisions",
        ),
        _entity(
            name="radar_source_signals",
            primary_key="signal_id",
            write_model="append_only",
            idempotency="source_event_candidate_signal",
            source="source_events",
        ),
        _entity(
            name="radar_snapshots",
            primary_key="snapshot_id",
            write_model="append_only",
            idempotency="window_parameters_formula_version",
            source="radar_scores",
        ),
        _entity(
            name="job_runs",
            primary_key="run_id",
            write_model="append_only",
            idempotency="job_id_idempotency_key",
            source="job_runs",
        ),
    ]


def _entity(
    *,
    name: str,
    primary_key: str,
    write_model: str,
    idempotency: str,
    source: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "primary_key": primary_key,
        "write_model": write_model,
        "idempotency": idempotency,
        "source": source,
        "required_columns": _required_columns_for_entity(name),
    }


def _required_columns_for_entity(name: str) -> list[str]:
    columns_by_entity = {
        "narratives": ["narrative_id", "name", "trust_status", "payload_json"],
        "stock_narrative_mappings": [
            "stock_code",
            "narrative_id",
            "trust_status",
            "payload_json",
        ],
        "evidence_packs": ["evidence_pack_id", "stock_code", "narrative_id"],
        "source_events": ["event_id", "source_type", "event_time", "payload_json"],
        "candidate_narratives": [
            "candidate_narrative_id",
            "name",
            "trust_status",
            "payload_json",
        ],
        "review_actions": [
            "review_action_id",
            "candidate_narrative_id",
            "action",
            "reviewed_at",
        ],
        "promotion_decisions": [
            "promotion_decision_id",
            "candidate_narrative_id",
            "target_narrative_id",
            "review_action_id",
        ],
        "radar_source_signals": ["signal_id", "source_event_id", "narrative_id"],
        "radar_snapshots": [
            "snapshot_id",
            "window_start",
            "window_end",
            "formula_version",
        ],
        "job_runs": ["run_id", "job_id", "started_at", "status"],
    }
    return columns_by_entity.get(name, [])


def _duration_ms(started_at: str, finished_at: str) -> int:
    try:
        started = datetime.fromisoformat(started_at)
        finished = datetime.fromisoformat(finished_at)
    except ValueError:
        return 0
    return max(0, int((finished - started).total_seconds() * 1000))


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


def _latest_promotions_by_candidate(
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for item in _list(payload.get("items")):
        candidate_id = str(item.get("candidate_narrative_id") or "")
        if candidate_id:
            latest[candidate_id] = item
    return latest


def _review_workflow_item(
    *,
    candidate: dict[str, Any],
    latest_action: dict[str, Any],
    promotion_decision: dict[str, Any],
) -> dict[str, Any]:
    queue_item = _review_queue_item(
        candidate=candidate,
        latest_action=latest_action,
    )
    candidate_id = str(candidate["candidate_narrative_id"])
    promotion_decision_id = str(promotion_decision.get("promotion_decision_id") or "")
    workflow_state = (
        "trusted_validated"
        if promotion_decision_id
        else str(queue_item.get("status") or "pending_review")
    )
    return {
        "workflow_item_id": f"RWF_{candidate_id}",
        "candidate_narrative_id": candidate_id,
        "candidate_name": str(candidate.get("name") or candidate_id),
        "trust_status": str(candidate.get("trust_status") or "candidate_untrusted"),
        "workflow_state": workflow_state,
        "review_status": str(queue_item.get("status") or ""),
        "recommended_action": str(queue_item.get("recommended_action") or ""),
        "preflight_result": str(queue_item.get("preflight_result") or ""),
        "missing_gates": _strings(queue_item.get("missing_gates")),
        "latest_review_action": latest_action,
        "promotion_decision_id": promotion_decision_id,
        "promotion_decision": promotion_decision,
        "audit_trail": {
            "latest_review_action_id": str(
                latest_action.get("review_action_id") or ""
            ),
            "reviewed_by": str(latest_action.get("reviewed_by") or ""),
            "action": str(latest_action.get("action") or ""),
            "reviewed_at": str(latest_action.get("reviewed_at") or ""),
            "review_note": str(latest_action.get("review_note") or ""),
            "promotion_decision_id": promotion_decision_id,
        },
        "links": {
            "candidate_detail": (
                f"/api/v1/narratives/candidates/{candidate_id}"
            ),
            "promotion_preflight": "/api/v1/narratives/promotion/preflight",
            "promotion_commit": "/api/v1/narratives/promotion/commit",
        },
    }


def _workflow_summary(items: list[dict[str, Any]]) -> dict[str, int]:
    summary = {state: 0 for state in REVIEW_WORKFLOW_STATES}
    for item in items:
        state = str(item.get("workflow_state") or "")
        summary[state] = summary.get(state, 0) + 1
    return summary


def _render_review_workflow_row(item: dict[str, Any]) -> str:
    audit = _mapping(item.get("audit_trail"))
    review_action = audit.get("action") or "none"
    promotion_id = item.get("promotion_decision_id") or "none"
    return (
        "<tr>"
        f"<td><code>{_html(item.get('candidate_narrative_id'))}</code><br />"
        f"{_html(item.get('candidate_name'))}</td>"
        f"<td>{_html(item.get('workflow_state'))}</td>"
        f"<td>{_html(item.get('preflight_result'))}<br />"
        f"missing: {_html(', '.join(_strings(item.get('missing_gates'))) or 'none')}</td>"
        f"<td>{_html(review_action)}<br />"
        f"{_html(audit.get('reviewed_by') or 'unreviewed')}</td>"
        f"<td>{_html(promotion_id)}</td>"
        "</tr>"
    )


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


def _html(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
