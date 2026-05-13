import json
import subprocess
import sys

from src import main as main_module
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


def test_optional_announcement_evidence_is_disclosed_and_added_to_outputs(tmp_path):
    class FakeAnnouncementProvider:
        provider_name = "cninfo-announcement"
        provider_version = "cninfo-announcement-v1"
        source_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
        degradation_events: list[dict[str, str]] = []

        def get_announcements(
            self,
            stock_codes: list[str],
            as_of_date: str,
            start_date: str | None = None,
        ) -> dict:
            assert "NVDA" in stock_codes
            assert as_of_date == "2026-05-13"
            assert start_date == "2026-05-01"
            return {
                "version": self.provider_version,
                "data_quality": "fresh",
                "announcements": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "title": "2026年度业绩预增公告",
                        "category": "业绩预告",
                        "announcement_date": "2026-05-12",
                        "source": "cninfo",
                        "source_url": "https://static.cninfo.com.cn/finalpage/1.PDF",
                    }
                ],
                "missing_stock_codes": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_announcement_evidence=True,
        announcement_start_date="2026-05-01",
        announcement_provider=FakeAnnouncementProvider(),
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()

    announcement_layer = scoring["provider_foundation"]["layers"]["announcements"]
    generated_evidence = raw["announcement_evidence"]["evidence"]

    assert scoring["metadata"]["data_quality"] == "partial"
    assert announcement_layer["provider_name"] == "cninfo-announcement"
    assert announcement_layer["data_quality"] == "fresh"
    assert announcement_layer["is_mock"] is False
    assert raw["announcements"]["version"] == "cninfo-announcement-v1"
    assert raw["announcement_evidence"]["data_quality"] == "fresh"
    assert len(generated_evidence) == 2
    assert {item["narrative_id"] for item in generated_evidence} == {
        "N_AI_INFRA",
        "N_SEMI_CAPEX",
    }
    assert any(item["source"] == "cninfo_announcement" for item in raw["evidence"])
    assert "PDF content has not been parsed" in generated_evidence[0]["summary"]
    assert "Announcements" in markdown
    assert "cninfo-announcement" in markdown
    assert "Announcements" in html
    assert "cninfo-announcement" in html


def test_cli_include_cninfo_announcements_passes_options_to_pipeline(
    tmp_path, monkeypatch
):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "000001",
            "--include-cninfo-announcements",
            "--announcement-start-date",
            "2026-05-01",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["fund_code"] == "000001"
    assert captured["include_announcement_evidence"] is True
    assert captured["announcement_start_date"] == "2026-05-01"


def test_cli_rejects_announcement_start_date_without_cninfo_opt_in(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--announcement-start-date",
        "2026-05-01",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--announcement-start-date requires --include-cninfo-announcements" in result.stderr
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


def test_pipeline_surfaces_multi_match_precision_flags(tmp_path, monkeypatch):
    def fake_fetcher(_url: str) -> dict:
        return {
            "Success": True,
            "Expansion": "2026-03-31",
            "Datas": {
                "fundStocks": [
                    {
                        "GPDM": "300604",
                        "GPJC": "长川科技",
                        "JZBL": "6.46",
                        "PCTNVCHG": "0",
                        "INDEXNAME": "电子",
                    }
                ]
            },
        }

    monkeypatch.setattr(eastmoney_module, "_fetch_json", fake_fetcher)

    artifacts = run_pipeline(
        fund_code="001475",
        provider_mode="eastmoney",
        output_dir=tmp_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()

    flagged_mappings = [
        mapping
        for mapping in raw["stock_narrative_mappings"]
        if mapping.get("precision_flag") == "multi_match_fallback"
    ]

    assert len(flagged_mappings) == 2
    assert {mapping["confidence"] for mapping in flagged_mappings} == {0.42}
    assert all(mapping["needs_review"] is True for mapping in flagged_mappings)
    assert raw["mapping_precision_flags"] == scoring["mapping_precision_flags"]
    assert raw["mapping_precision_flags"][0]["recommended_action"] == "manual_review"
    assert raw["mapping_precision_flags"][0]["narrative_ids"] == [
        "N_SEMI_CAPEX",
        "N_DEFENSE_AEROSPACE",
    ]
    assert "Mapping Precision Flags" in markdown
    assert "needs review" in markdown
    assert "长川科技" in html
    assert "Mapping Precision Flags" in html


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
