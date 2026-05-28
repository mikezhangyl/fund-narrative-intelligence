import json

from scripts import validate_stock_narrative_service_acceptance


def test_stock_narrative_service_acceptance_runs_end_to_end(tmp_path):
    exit_code = validate_stock_narrative_service_acceptance.main(
        ["--output-dir", str(tmp_path)]
    )

    summary = json.loads((tmp_path / "acceptance_summary.json").read_text())
    report = json.loads(
        (tmp_path / "fund_holding_exposure_report.json").read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert summary["status"] == "completed"
    assert summary["conformance_status"] == "completed"
    assert summary["provider_smoke_status"] == "completed"
    assert summary["provider_smoke_source"] == "narrative_service"
    assert summary["fallback_smoke_status"] == "completed"
    assert summary["fallback_smoke_source"] == "local_prototype"
    assert "NARRATIVE_SERVICE_FALLBACK" in summary["fallback_smoke_warning_codes"]
    assert summary["report_status"] == "completed"
    assert summary["ci_gate"] == {
        "mode": "deterministic_local",
        "requires_live_credentials": False,
        "mandatory_slice_checks": [
            "contract_endpoint_conformance",
            "provider_smoke_service_first",
            "provider_smoke_local_fallback",
            "service_backed_report_source_disclosure",
        ],
        "full_release_checks": [
            "uv run pytest -q",
            "uv run python scripts/validate_stock_narrative_service_acceptance.py",
            "live_gateway_provider_checks_when_credentials_exist",
        ],
        "output_policy": {
            "default_root": "outputs/stock_narrative_service_acceptance/",
            "source_control": "generated_outputs_ignored",
        },
    }
    assert "provider_fallback_smoke" in summary["artifacts"]
    assert report["narrative_source"]["source"] == "narrative_service"
    assert report["summary"]["holding_count"] == 2
    assert report["summary"]["narrative_exposure_count"] >= 1
