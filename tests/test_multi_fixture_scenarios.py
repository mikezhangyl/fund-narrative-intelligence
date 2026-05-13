import json
import subprocess
import sys

from src.orchestrator import run_all_fixture_pipelines, run_pipeline
from src.providers.mock import MockDataProvider


def test_mock_fixtures_cover_multiple_scenarios():
    fund_codes = MockDataProvider().list_fund_codes()

    assert fund_codes == ["000001", "000002", "000003"]


def test_scenario_funds_produce_different_primary_stages(tmp_path):
    stages = {}

    for fund_code in MockDataProvider().list_fund_codes():
        run_pipeline(fund_code=fund_code, output_dir=tmp_path)
        scoring = json.loads((tmp_path / f"fund_{fund_code}_scoring.json").read_text())
        stages[fund_code] = scoring["primary_narrative"]["state"]["stage"]

    assert stages["000001"] == "strengthening"
    assert stages["000002"] == "crowded"
    assert stages["000003"] == "dead"


def test_reviewed_secondary_stage_after_calibration(tmp_path):
    artifacts = run_pipeline(fund_code="000001", output_dir=tmp_path)
    scoring = json.loads(artifacts["scoring"].read_text())
    stages_by_narrative_id = {
        item["narrative_id"]: item["state"]["stage"]
        for item in scoring["all_narratives"]
    }

    assert stages_by_narrative_id["N_AI_APPS"] == "strengthening"


def test_run_all_fixture_pipelines_generates_artifacts_for_every_fixture(tmp_path):
    results = run_all_fixture_pipelines(output_dir=tmp_path)

    assert sorted(results) == ["000001", "000002", "000003"]
    for fund_code in results:
        for suffix in ["raw.json", "scoring.json", "report.md", "report.html"]:
            assert (tmp_path / f"fund_{fund_code}_{suffix}").exists()


def test_cli_run_all_fixtures_generates_batch_outputs(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--run-all-fixtures",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    assert "000001" in result.stdout
    assert "000002" in result.stdout
    assert "000003" in result.stdout
    assert (tmp_path / "fund_000003_report.html").exists()
