import json
import subprocess
import sys

from src.orchestrator import run_pipeline
from src.providers import eastmoney as eastmoney_module


def test_cli_generates_required_v1_artifacts(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr

    raw_path = tmp_path / "fund_000001_raw.json"
    scoring_path = tmp_path / "fund_000001_scoring.json"
    markdown_path = tmp_path / "fund_000001_report.md"
    html_path = tmp_path / "fund_000001_report.html"

    for path in [raw_path, scoring_path, markdown_path, html_path]:
        assert path.exists(), f"missing {path}"

    raw = json.loads(raw_path.read_text())
    scoring = json.loads(scoring_path.read_text())
    markdown = markdown_path.read_text()
    html = html_path.read_text()

    assert raw["metadata"]["fund_code"] == "000001"
    assert raw["metadata"]["provider_set_version"] == "mock-v1"
    assert raw["fund"]["provider_metadata"]["data_quality"] == "mock"
    assert len(raw["holdings"]) == 10

    assert scoring["metadata"]["scoring_model_version"] == "scoring-v1"
    assert scoring["primary_narrative"]["narrative_id"]
    assert "interpretation" in scoring["primary_narrative"]
    assert len(scoring["secondary_narratives"]) >= 2
    assert "earnings_score" in scoring["primary_narrative"]["state"]["dimensions"]
    assert scoring["mapping_coverage"]["coverage_ratio"] > 0

    assert "不构成投资建议" in markdown
    assert "不构成投资建议" in html
    assert "Mapping Coverage" in markdown
    assert "Mapping Coverage" in html
    assert "Data Source Notice" in markdown
    assert "Data Source Notice" in html
    assert "Mock 数据" in markdown
    assert "Mock 数据" in html
    assert "Interpretation" in markdown
    assert "Interpretation" in html
    assert "AI Infrastructure" in markdown


def test_real_provider_mode_degrades_to_mock_without_crashing(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--provider-mode",
        "real",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr

    raw = json.loads((tmp_path / "fund_000001_raw.json").read_text())
    scoring = json.loads((tmp_path / "fund_000001_scoring.json").read_text())

    assert raw["fund"]["provider_metadata"]["data_quality"] == "mock"
    assert raw["degradation_events"]
    assert raw["provider_foundation"]["disclosure_required"] is True
    assert scoring["metadata"]["data_quality"] == "mock"
    assert scoring["provider_foundation"]["effective_data_quality"] == "mock"

    markdown = (tmp_path / "fund_000001_report.md").read_text()
    html = (tmp_path / "fund_000001_report.html").read_text()

    assert "Data Source Notice" in markdown
    assert "provider_fallback" in markdown
    assert "Mock 数据" in markdown
    assert "provider_fallback" in html


def test_cli_provider_diagnostics_prints_foundation_without_artifacts(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--provider-diagnostics",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr

    diagnostics = json.loads(result.stdout)

    assert diagnostics["fund_code"] == "000001"
    assert diagnostics["provider_mode"] == "mock"
    assert diagnostics["provider_foundation"]["effective_data_quality"] == "mock"
    assert diagnostics["provider_foundation"]["disclosure_required"] is True
    assert "Mock 数据" in diagnostics["provider_foundation"]["disclosure_message"]
    assert not list(tmp_path.glob("*"))


def test_cli_provider_diagnostics_shows_real_mode_fallback(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--provider-mode",
        "real",
        "--provider-diagnostics",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr

    diagnostics = json.loads(result.stdout)
    events = diagnostics["provider_foundation"]["degradation_events"]

    assert diagnostics["provider_mode"] == "real"
    assert diagnostics["provider_foundation"]["effective_data_quality"] == "mock"
    assert events[0]["type"] == "provider_fallback"
    assert "provider_fallback" in diagnostics["provider_foundation"]["disclosure_message"]
    assert not list(tmp_path.glob("*"))


def test_eastmoney_holdings_with_mock_intelligence_is_disclosed_as_partial(
    tmp_path, monkeypatch
):
    def fake_fetcher(_url: str) -> dict:
        return {
            "Success": True,
            "Expansion": "2026-03-31",
            "Datas": {
                "fundStocks": [
                    {
                        "GPDM": "600519",
                        "GPJC": "贵州茅台",
                        "JZBL": "18.33",
                        "PCTNVCHG": "2.95",
                        "INDEXNAME": "食品饮料",
                    },
                    {
                        "GPDM": "000858",
                        "GPJC": "五粮液",
                        "JZBL": "16.14",
                        "PCTNVCHG": "1.49",
                        "INDEXNAME": "食品饮料",
                    },
                ]
            },
        }

    monkeypatch.setattr(eastmoney_module, "_fetch_json", fake_fetcher)

    artifacts = run_pipeline(
        fund_code="161725",
        provider_mode="eastmoney",
        output_dir=tmp_path,
    )

    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()

    foundation = scoring["provider_foundation"]

    assert scoring["metadata"]["data_quality"] == "partial"
    assert foundation["effective_data_quality"] == "partial"
    assert foundation["layers"]["holdings"]["data_quality"] == "fresh"
    assert foundation["layers"]["evidence"]["data_quality"] == "mock"
    assert "混合数据源" in markdown
    assert "Eastmoney" in markdown
    assert "Mock fixtures" in markdown
    assert "混合数据源" in html


def test_report_generation_handles_unmapped_real_holdings(tmp_path):
    from src.modules.report_writer.writer import write_reports

    scoring_payload = {
        "metadata": {
            "fund_code": "123456",
            "as_of_date": "2026-03-31",
            "data_quality": "fresh",
            "scoring_model_version": "scoring-v1",
        },
        "fund": {"fund_code": "123456", "fund_name": "Unmapped Fund"},
        "holdings": [
            {"stock_code": "600000", "stock_name": "浦发银行", "weight": 0.1}
        ],
        "primary_narrative": None,
        "secondary_narratives": [],
        "supporting_evidence": [],
        "risk_evidence": [],
    }

    paths = write_reports(scoring_payload, tmp_path)

    markdown = paths["markdown"].read_text()
    assert "No mapped narrative exposure" in markdown
    assert "不构成投资建议" in markdown
