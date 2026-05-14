import json

import pytest
from src.errors import ProviderContractError
from src.modules.workspace_snapshot.builder import build_workspace_snapshot
from src.orchestrator import run_pipeline
from src.validation import validate_workspace_snapshot_payload


def test_build_workspace_snapshot_from_output_directory(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)

    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())

    validate_workspace_snapshot_payload(snapshot)
    assert snapshot_path.name == "fund_000001_workspace_snapshot.json"
    assert snapshot["version"] == "workspace-snapshot-v1"
    assert snapshot["fund_code"] == "000001"
    assert snapshot["artifact_manifest"]["artifacts"]["source_table"]["path"] == (
        "fund_000001_source_table.json"
    )
    assert snapshot["source_table"]["layers"][0]["source_url"].startswith(
        "mock://fixtures/"
    )
    assert snapshot["review_queue"]["candidate_review_queue"]["version"] == (
        "candidate-review-queue-v1"
    )
    assert snapshot["approval_workflow"]["status"] == "ready_for_future_web"
    assert snapshot["approval_workflow"]["read_only"] is True
    assert snapshot["narratives"]["primary"]["narrative_id"]


def test_workspace_snapshot_validation_rejects_identity_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["source_table"]["fund_code"] = "999999"

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "source table fund_code mismatch" in str(exc.value)


def test_build_workspace_snapshot_rejects_missing_report_file(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    (tmp_path / "fund_000001_report.md").unlink()

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path)

    assert "manifest artifact markdown does not exist" in str(exc.value)


def test_build_workspace_snapshot_rejects_external_output_path(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)

    with pytest.raises(ValueError) as exc:
        build_workspace_snapshot(tmp_path, output_path=tmp_path.parent / "snapshot.json")

    assert "workspace snapshot output must stay in artifact directory" in str(exc.value)


def test_workspace_snapshot_validation_rejects_review_queue_identity_drift(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["review_queue"]["metadata"]["fund_code"] = "999999"

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "review queue fund_code mismatch" in str(exc.value)


def test_workspace_snapshot_validation_rejects_incomplete_narrative_payload(tmp_path):
    run_pipeline(fund_code="000001", provider_mode="mock", output_dir=tmp_path)
    snapshot_path = build_workspace_snapshot(tmp_path)
    snapshot = json.loads(snapshot_path.read_text())
    snapshot["narratives"]["primary"] = {}

    with pytest.raises(ProviderContractError) as exc:
        validate_workspace_snapshot_payload(snapshot)

    assert "narratives.primary missing required fields" in str(exc.value)
