import json
from pathlib import Path

import yaml
from scripts import run_narrative_service_conformance_probe

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_narrative_service_conformance_probe_reports_not_configured(
    monkeypatch,
    tmp_path,
):
    monkeypatch.delenv("NARRATIVE_SERVICE_URL", raising=False)

    exit_code = run_narrative_service_conformance_probe.main(
        ["--output-dir", str(tmp_path)]
    )

    payload = json.loads(
        (tmp_path / "narrative_service_conformance_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert payload["result"]["status"] == "not_configured"
    assert payload["result"]["base_url"] == ""
    assert payload["result"]["endpoint_results"] == []


def test_narrative_service_conformance_probe_checks_contract_endpoints(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("NARRATIVE_SERVICE_URL", "http://127.0.0.1:9999")
    requested: list[tuple[str, str]] = []

    def fake_request_json(*, method, url, payload, timeout_seconds):
        del timeout_seconds
        requested.append((method, url))
        if url.endswith("/review-actions") and method == "POST":
            assert payload == {
                "candidate_narrative_id": "C_AUTO_3D71C39000",
                "action": "defer",
                "reviewed_by": "conformance-probe",
                "review_note": "Contract smoke only; no trusted promotion.",
            }
        if url.endswith("/promotion/preflight") and method == "POST":
            assert payload == {"candidate_narrative_id": "C_AUTO_3D71C39000"}
        return {
            "status": "available",
            "source": "narrative_service",
            "provider": "fake-narrative-service",
            "provider_version": "fake-v1",
            "data": {},
            "warnings": [],
            "trust_metadata": {"trust_status": "candidate_untrusted"},
        }

    monkeypatch.setattr(
        run_narrative_service_conformance_probe,
        "_request_json",
        fake_request_json,
    )

    exit_code = run_narrative_service_conformance_probe.main(
        ["--output-dir", str(tmp_path)]
    )

    payload = json.loads(
        (tmp_path / "narrative_service_conformance_report.json").read_text(
            encoding="utf-8"
        )
    )
    endpoint_results = payload["result"]["endpoint_results"]
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )
    contract_endpoints = {
        endpoint["method"] + " " + endpoint["path"]
        for endpoint in contract["endpoints"]
    }
    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert {
        result["method"] + " " + result["path"] for result in endpoint_results
    } == contract_endpoints
    assert {
        result["method"] + " " + result["path"] for result in endpoint_results
    } >= {
        "GET /api/v1/narratives/registry",
        "GET /api/v1/narratives/mappings",
        "POST /api/v1/narratives/intake/events",
        "GET /api/v1/narratives/evidence-packs",
        "GET /api/v1/narratives/trust-audits/latest",
        "GET /api/v1/narratives/ops/summary",
        "GET /api/v1/narratives/review-queue",
        "GET /api/v1/narratives/review-actions",
        "POST /api/v1/narratives/review-actions",
        "POST /api/v1/narratives/promotion/preflight",
    }
    assert all(result["status"] == "passed" for result in endpoint_results)
    assert requested
    assert requested[0][1].startswith("http://127.0.0.1:9999/api/v1/narratives/")


def test_narrative_service_contract_declares_versioning_and_error_semantics():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    policy = contract["api_policy"]

    assert policy["base_path"] == "/api/v1/narratives"
    assert policy["current_version"] == "v1"
    assert policy["versioning_rule"] == "additive_non_breaking"
    assert policy["compatibility_rule"] == (
        "new endpoints and optional fields may be added without breaking existing probes"
    )
    assert policy["required_envelope_fields"] == [
        "status",
        "source",
        "provider",
        "provider_version",
        "data",
        "warnings",
        "trust_metadata",
    ]
    assert policy["error_semantics"]["missing_id"]["status"] == "missing"
    assert policy["error_semantics"]["invalid_request"]["http_status"] == 400
    assert all(
        endpoint["path"].startswith(policy["base_path"])
        for endpoint in contract["endpoints"]
    )


def test_narrative_service_contract_declares_append_only_ledger_policy():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    policy = contract["storage_policy"]
    ledgers = policy["append_only_ledgers"]

    assert policy["current_store"] == "json_file_ledgers_v1"
    assert ledgers["candidate_intake_events"]["version"] == "service-intake-events-v1"
    assert ledgers["narrative_review_actions"]["version"] == (
        "narrative-review-actions-v1"
    )
    assert ledgers["promotion_decisions"]["status"] == "reserved"
    assert "source_metadata" in ledgers["candidate_intake_events"]["required_record_fields"]
    assert "source_metadata" in ledgers["narrative_review_actions"]["required_record_fields"]
    assert policy["mutation_policy"]["failed_intake_writes"] == "none"
    assert "registry" in policy["mutation_policy"]["review_actions_must_not_mutate"]
    assert policy["migration"]["http_contract_change_allowed"] is False


def test_narrative_service_contract_declares_identity_policy():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    policy = contract["identity_policy"]

    assert policy["explicit_id_rule"] == "preserve_non_empty_external_ids"
    assert policy["deterministic_fallbacks"]["candidate_narrative_id"]["prefix"] == (
        "C_INTAKE"
    )
    assert policy["deterministic_fallbacks"]["source_event_id"]["prefix"] == "EVT"
    assert policy["deterministic_fallbacks"]["evidence_pack_id"]["fields"] == [
        "stock_code",
        "narrative_id",
    ]
    assert policy["deterministic_fallbacks"]["candidate_mapping_id"]["prefix"] == (
        "CMAP"
    )
    assert policy["review_action_id"]["idempotency_key_rule"] == (
        "same candidate, action, reviewer, and idempotency_key returns the existing decision"
    )
    assert policy["unknown_id_semantics"]["candidate_narrative_id"] == (
        "reject_without_ledger_write"
    )


def test_narrative_service_contract_declares_provider_aware_intake_policy():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    policy = contract["intake_policy"]

    assert policy["supported_source_types"] == [
        "news",
        "announcement",
        "manual",
        "social_future",
    ]
    assert policy["provider_preference"]["news"][:2] == [
        "gateway_news_briefs",
        "tushare_news",
    ]
    assert policy["provider_preference"]["announcement"][:2] == [
        "gateway_announcements",
        "tushare_announcements",
    ]
    assert policy["crawler_policy"]["public_news_websites"] == (
        "fallback_only_after_permission_review"
    )
    assert policy["outputs"]["candidate_items_trust_status"] == "candidate_untrusted"
    assert policy["outputs"]["reinforcement_promotion_effect"] == "none"
    assert policy["required_source_metadata_fields"] == [
        "provider",
        "provider_version",
        "permission_status",
        "degradation_state",
    ]


def test_narrative_service_contract_declares_trust_state_machine():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    machine = contract["trust_state_machine"]

    assert machine["record_states"] == [
        "local_fixture",
        "candidate_untrusted",
        "reviewed_experimental",
        "trusted_validated",
    ]
    assert machine["queue_statuses"] == [
        "pending_review",
        "approved_blocked_by_evidence",
        "ready_for_trust_audit",
        "rejected",
        "deferred",
    ]
    assert machine["state_aliases"]["untrusted_experimental"] == (
        "reviewed_experimental"
    )
    assert machine["state_aliases"]["reviewed_untrusted"] == (
        "reviewed_experimental"
    )
    assert machine["operations"]["intake"]["record_transitions"] == [
        {"from": "local_fixture", "to": "candidate_untrusted"}
    ]
    assert machine["operations"]["review_action"]["record_transitions"] == []
    assert machine["operations"]["preflight"]["write_behavior"] == "read_only"
    assert machine["operations"]["promotion"]["record_transition"] == {
        "from": "candidate_untrusted",
        "to": "trusted_validated",
        "required_queue_status": "ready_for_trust_audit",
    }
    for operation in ("intake", "review_action", "preflight"):
        assert "trusted_validated" in machine["operations"][operation][
            "forbidden_to_record_states"
        ]


def test_narrative_service_contract_declares_promotion_transaction_boundary():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    boundary = contract["promotion_transaction_boundary"]

    assert boundary["command_surface"] == {
        "mode": "http_endpoint",
        "endpoint": "/api/v1/narratives/promotion/commit",
        "current_status": "enabled_explicit_gate_commit",
    }
    assert boundary["command_required_fields"] == [
        "candidate_narrative_id",
        "target_narrative_id",
        "review_action_id",
        "trust_audit_id",
        "promoted_by",
        "promotion_note",
    ]
    assert boundary["atomic_write_set"] == [
        "trusted_registry_record",
        "trusted_stock_mapping_record",
        "trusted_evidence_pack_record",
        "promotion_decision_ledger_record",
    ]
    assert boundary["transaction_rule"] == "all_or_none"
    assert boundary["failure_behavior"]["partial_write_allowed"] is False
    assert boundary["failure_behavior"]["rollback_required"] is True
    assert boundary["audit_record_schema"]["record_type"] == "promotion_decision"
    assert boundary["audit_record_schema"]["decision_id_prefix"] == "PD"
    assert "promotion_decision_id" in boundary["audit_record_schema"][
        "required_fields"
    ]
    assert boundary["forbidden_callers"] == [
        "candidate_intake",
        "review_action",
        "promotion_preflight",
        "trust_audit_read",
    ]


def test_narrative_service_contract_declares_observability_policy():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    policy = contract["observability_policy"]

    assert policy["current_status"] == "minimal_diagnostics_no_heavy_infra"
    assert policy["diagnostics_schema"]["version"] == (
        "narrative-operational-diagnostics-v1"
    )
    assert policy["diagnostics_schema"]["required_fields"] == [
        "schema_version",
        "provider_source",
        "status_summary",
        "queue_summary",
        "audit_status",
        "product_data_gaps",
        "system_failures",
    ]
    assert "/api/v1/narratives/ops/summary" in policy["snapshot_surfaces"][
        "endpoints"
    ]
    assert policy["snapshot_surfaces"]["reports"] == [
        "fund_holding_exposure",
        "fund_exposure_comparison",
        "fund_narrative_exposure_matrix",
    ]
    assert policy["failure_classification"]["product_data_gap"] == (
        "business data missing while service/runtime remains healthy"
    )
    assert policy["failure_classification"]["system_failure"] == (
        "service/runtime/provider operation failed or returned invalid data"
    )
    assert policy["structured_log_shape"]["fields"] == [
        "timestamp",
        "level",
        "event",
        "request_id",
        "source",
        "provider",
        "status",
        "classification",
        "warning_codes",
    ]
    assert policy["forbidden_infrastructure"] == [
        "proxy_rotation",
        "browser_automation",
        "anti_detect_runtime",
    ]


def test_narrative_service_contract_declares_candidate_detail_endpoint():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    endpoint = next(
        item
        for item in contract["endpoints"]
        if item["path"] == "/api/v1/narratives/candidates/{candidate_narrative_id}"
    )

    assert endpoint["method"] == "GET"
    assert endpoint["conformance_path"] == (
        "/api/v1/narratives/candidates/C_AUTO_3D71C39000"
    )
    assert endpoint["missing_id_behavior"] == "missing_envelope"


def test_narrative_service_contract_declares_evidence_pack_detail_endpoint():
    contract = yaml.safe_load(
        (PROJECT_ROOT / "config" / "narrative_service_contract.yaml").read_text(
            encoding="utf-8"
        )
    )

    endpoint = next(
        item
        for item in contract["endpoints"]
        if item["path"] == "/api/v1/narratives/evidence-packs/{evidence_pack_id}"
    )

    assert endpoint["method"] == "GET"
    assert endpoint["conformance_path"] == (
        "/api/v1/narratives/evidence-packs/EPACK_7AF6C98698"
    )
    assert endpoint["alternate_lookup"] == (
        "/api/v1/narratives/evidence-packs/detail?stock_code=600519&narrative_id=N_BAIJIU_CONSUMPTION"
    )
    assert endpoint["missing_id_behavior"] == "missing_envelope"


def test_fni_report_entrypoints_do_not_import_narrative_service_internals():
    report_paths = [
        PROJECT_ROOT / "src" / "scanners" / "fund_holding_exposure_report.py",
        PROJECT_ROOT / "src" / "scanners" / "fund_exposure_comparison_report.py",
        PROJECT_ROOT / "src" / "scanners" / "fund_narrative_exposure_matrix_report.py",
        PROJECT_ROOT / "scripts" / "run_fund_holding_exposure_report.py",
        PROJECT_ROOT / "scripts" / "run_fund_exposure_comparison_report.py",
        PROJECT_ROOT / "scripts" / "run_fund_narrative_exposure_matrix_report.py",
    ]

    offenders = [
        path
        for path in report_paths
        if "stock_narrative_service" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
