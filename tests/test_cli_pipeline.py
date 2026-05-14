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
    manifest_path = tmp_path / "fund_000001_manifest.json"
    markdown_path = tmp_path / "fund_000001_report.md"
    html_path = tmp_path / "fund_000001_report.html"

    for path in [raw_path, scoring_path, manifest_path, markdown_path, html_path]:
        assert path.exists(), f"missing {path}"

    raw = json.loads(raw_path.read_text())
    scoring = json.loads(scoring_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    markdown = markdown_path.read_text()
    html = html_path.read_text()

    assert raw["metadata"]["fund_code"] == "000001"
    assert raw["metadata"]["provider_set_version"] == "mock-v1"
    assert raw["fund"]["provider_metadata"]["data_quality"] == "mock"
    assert raw["fund"]["provider_metadata"]["source_url"] == (
        "mock://fixtures/fund_000001.json"
    )
    assert len(raw["holdings"]) == 10

    assert scoring["metadata"]["scoring_model_version"] == "scoring-v1"
    assert scoring["provider_foundation"]["layers"]["holdings"]["source_url"] == (
        "mock://fixtures/fund_000001.json"
    )
    assert scoring["provider_foundation"]["layers"]["narrative_registry"][
        "source_url"
    ] == "mock://fixtures/narrative_registry.json"
    assert manifest["version"] == "pipeline-artifact-manifest-v1"
    assert manifest["fund_code"] == "000001"
    assert manifest["data_quality"] == "mock"
    assert manifest["web_ready"] is True
    assert manifest["artifacts"]["raw"]["path"] == "fund_000001_raw.json"
    assert manifest["artifacts"]["scoring"]["path"] == "fund_000001_scoring.json"
    assert manifest["artifacts"]["review_queue"]["path"] == (
        "fund_000001_review_queue.json"
    )
    assert manifest["artifacts"]["markdown"]["path"] == "fund_000001_report.md"
    assert manifest["artifacts"]["html"]["path"] == "fund_000001_report.html"
    assert manifest["provider_foundation"] == scoring["provider_foundation"]
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
    assert "mock://fixtures/fund_000001.json" in markdown
    assert "mock://fixtures/fund_000001.json" in html
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
    assert diagnostics["provider_foundation"]["layers"]["holdings"]["source_url"] == (
        "mock://fixtures/fund_000001.json"
    )
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
    assert raw["mapping_rationales"] == scoring["mapping_rationales"]
    assert len(raw["mapping_rationales"]) == 2
    assert {
        tuple(rationale["matched_terms"]) for rationale in raw["mapping_rationales"]
    } == {("电子",), ("长川科技",)}
    assert all(
        rationale["needs_review"] is True
        for rationale in raw["mapping_rationales"]
    )
    assert "Mapping Precision Flags" in markdown
    assert "Mapping Rationales" in markdown
    assert "Matched registry terms against stock code/name/industry" in markdown
    assert "needs review" in markdown
    assert "长川科技" in html
    assert "Mapping Precision Flags" in html
    assert "Mapping Rationales" in html


def test_pipeline_surfaces_broad_industry_precision_flags(tmp_path, monkeypatch):
    def fake_fetcher(_url: str) -> dict:
        return {
            "Success": True,
            "Expansion": "2026-03-31",
            "Datas": {
                "fundStocks": [
                    {
                        "GPDM": "123456",
                        "GPJC": "测试科技",
                        "JZBL": "10.00",
                        "PCTNVCHG": "0",
                        "INDEXNAME": "电子",
                    }
                ]
            },
        }

    monkeypatch.setattr(eastmoney_module, "_fetch_json", fake_fetcher)

    artifacts = run_pipeline(
        fund_code="320007",
        provider_mode="eastmoney",
        output_dir=tmp_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()

    assert raw["mapping_precision_flags"] == scoring["mapping_precision_flags"]
    assert raw["mapping_precision_flags"] == [
        {
            "type": "broad_industry_fallback",
            "severity": "watch",
            "stock_code": "123456",
            "stock_name": "测试科技",
            "industry": "电子",
            "weight": 0.1,
            "mapping_method": "registry_term_rule",
            "narrative_ids": ["N_SEMI_CAPEX"],
            "narratives": ["Semiconductor Capex Cycle"],
            "confidence_before": 0.52,
            "confidence_after": 0.48,
            "recommended_action": "curation_review",
        }
    ]
    assert raw["mapping_rationales"][0]["precision_flag"] == (
        "broad_industry_fallback"
    )
    assert raw["mapping_rationales"][0]["reason"] == (
        "Matched broad industry-only registry terms against holding industry: 电子."
    )
    assert "broad_industry_fallback" in markdown
    assert "curation review" in markdown
    assert "broad_industry_fallback" in html
    assert "curation review" in html


def test_pipeline_excludes_known_bad_mapping_candidates(tmp_path, monkeypatch):
    def fake_fetcher(_url: str) -> dict:
        return {
            "Success": True,
            "Expansion": "2026-03-31",
            "Datas": {
                "fundStocks": [
                    {
                        "GPDM": "688036",
                        "GPJC": "传音控股",
                        "JZBL": "6.00",
                        "PCTNVCHG": "0",
                        "INDEXNAME": "电子",
                    }
                ]
            },
        }

    monkeypatch.setattr(eastmoney_module, "_fetch_json", fake_fetcher)

    artifacts = run_pipeline(
        fund_code="320007",
        provider_mode="eastmoney",
        output_dir=tmp_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    review_queue = json.loads(artifacts["review_queue"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()

    assert raw["stock_narrative_mappings"] == []
    assert raw["mapping_coverage"]["coverage_ratio"] == 0
    assert raw["candidate_narrative_registry_version"] == "registry-v1"
    assert raw["candidate_narratives"] == scoring["candidate_narratives"]
    assert raw["candidate_narratives"] == [
        {
            "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "name": "Consumer Electronics Globalization",
            "canonical_taxonomy": "Technology Hardware",
            "status": "candidate",
            "source": "mapping_exclusion_review",
            "triggering_stock_codes": ["688036"],
            "related_exclusion_ids": ["EX_SEMI_688036"],
            "aliases": ["consumer electronics exports", "device globalization"],
            "related_terms": ["消费电子", "终端设备", "海外手机"],
            "rationale": (
                "Transsion is a device and overseas-market exposure candidate, "
                "not a semiconductor capex exposure."
            ),
            "human_review_status": "candidate",
            "reviewed_by": None,
            "reviewed_at": None,
            "first_seen_at": "2026-05-14",
            "last_updated_at": "2026-05-14",
        }
    ]
    assert raw["candidate_review_queue"] == scoring["candidate_review_queue"]
    assert artifacts["review_queue"].name == "fund_320007_review_queue.json"
    assert review_queue["metadata"] == scoring["metadata"]
    assert review_queue["fund"] == scoring["fund"]
    assert review_queue["provider_foundation"] == scoring["provider_foundation"]
    assert review_queue["candidate_review_queue"] == scoring[
        "candidate_review_queue"
    ]
    assert review_queue["candidate_narratives"] == scoring["candidate_narratives"]
    assert review_queue["excluded_mapping_candidates"] == scoring[
        "excluded_mapping_candidates"
    ]
    assert raw["candidate_review_queue"]["summary"] == {
        "total_count": 1,
        "pending_count": 1,
        "action_required": True,
    }
    assert raw["candidate_review_queue"]["items"][0]["review_item_id"] == (
        "RQ_C_CONSUMER_ELECTRONICS_GLOBALIZATION"
    )
    assert raw["candidate_review_queue"]["items"][0]["available_actions"] == [
        "approve",
        "reject",
        "defer",
    ]
    assert raw["candidate_review_queue"]["items"][0]["related_exclusions"][0][
        "stock_code"
    ] == "688036"
    assert raw["candidate_review_queue"]["items"][0]["promotion_action_template"][
        "candidate_narrative_id"
    ] == "C_CONSUMER_ELECTRONICS_GLOBALIZATION"
    assert raw["excluded_mapping_candidates"] == scoring[
        "excluded_mapping_candidates"
    ]
    assert raw["excluded_mapping_candidates"] == [
        {
            "type": "excluded_mapping_candidate",
            "exclusion_id": "EX_SEMI_688036",
            "stock_code": "688036",
            "stock_name": "传音控股",
            "industry": "电子",
            "weight": 0.06,
            "narrative_id": "N_SEMI_CAPEX",
            "narrative_name": "Semiconductor Capex Cycle",
            "method": "registry_term_rule",
            "matched_terms": ["电子"],
            "reason": (
                "Consumer electronics device exposure is too broad for "
                "Semiconductor Capex."
            ),
            "recommended_action": "candidate_narrative_review",
        }
    ]
    assert "Excluded Mapping Candidates" in markdown
    assert "Candidate Narratives For Review" in markdown
    assert "Consumer Electronics Globalization" in markdown
    assert "传音控股" in markdown
    assert "candidate_narrative_review" in html
    assert '<section class="candidate-narratives">' in html


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
