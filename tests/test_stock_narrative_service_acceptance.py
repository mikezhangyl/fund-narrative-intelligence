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
    assert summary["report_status"] == "completed"
    assert report["narrative_source"]["source"] == "narrative_service"
    assert report["summary"]["holding_count"] == 2
    assert report["summary"]["narrative_exposure_count"] >= 1

