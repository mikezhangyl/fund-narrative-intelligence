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
    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
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
