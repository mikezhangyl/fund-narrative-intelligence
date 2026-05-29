from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.errors import ProviderContractError
from src.modules.workspace_snapshot.builder import build_workspace_snapshot
from src.orchestrator import run_pipeline
from src.validation import validate_pipeline_artifact_manifest_payload

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_fund_report_manifest_contains_round2_contract_fields_and_html_json_links(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)

    contract = json.loads(
        (PROJECT_ROOT / "config" / "fund_report_artifact_contract.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads((tmp_path / "fund_000001_manifest.json").read_text())
    html = (tmp_path / "fund_000001_report.html").read_text(encoding="utf-8")

    assert contract["version"] == "fund-report-artifact-contract-v1"
    assert "run_id" in contract["required_manifest_fields"]
    validate_pipeline_artifact_manifest_payload(manifest)
    assert manifest["run_id"].startswith("fund_000001_")
    assert manifest["generated_at"]
    assert manifest["source_modes"]["provider_mode"] == "mock"
    assert manifest["source_modes"]["layers"]["holdings"]["data_quality"] == "mock"
    assert manifest["warning_counts"]["mock_layer_count"] > 0
    assert manifest["warning_counts"]["degradation_event_count"] == 0
    assert manifest["trust_states"] == {
        "candidate_outputs": "candidate_untrusted",
        "report_pack": "review_required",
        "trusted_promotion": "disabled",
    }
    assert manifest["artifacts"]["raw"]["source_control"] == "generated_output_only"
    assert manifest["artifacts"]["html"]["reader_surface"] is True
    assert 'href="fund_000001_raw.json"' in html
    assert 'href="fund_000001_scoring.json"' in html
    assert 'href="fund_000001_review_queue.json"' in html


def test_report_pack_validation_rejects_missing_artifact_file(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    (tmp_path / "fund_000001_raw.json").unlink()

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path)

    assert "manifest artifact raw does not exist" in str(exc.value)


def test_report_pack_validation_rejects_degraded_source_count_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    manifest_path = tmp_path / "fund_000001_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["warning_counts"]["mock_layer_count"] = 0

    with pytest.raises(ProviderContractError) as exc:
        validate_pipeline_artifact_manifest_payload(manifest)

    assert "warning_counts mock_layer_count mismatch" in str(exc.value)
