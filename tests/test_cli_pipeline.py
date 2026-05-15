import json
import subprocess
import sys

import pytest
from src import main as main_module
from src.config import FIXTURE_DIR
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
    review_queue_path = tmp_path / "fund_000001_review_queue.json"
    manifest_path = tmp_path / "fund_000001_manifest.json"
    source_table_path = tmp_path / "fund_000001_source_table.json"
    signal_trace_path = tmp_path / "fund_000001_signal_trace.json"
    markdown_path = tmp_path / "fund_000001_report.md"
    html_path = tmp_path / "fund_000001_report.html"

    for path in [
        raw_path,
        scoring_path,
        review_queue_path,
        manifest_path,
        source_table_path,
        signal_trace_path,
        markdown_path,
        html_path,
    ]:
        assert path.exists(), f"missing {path}"

    raw = json.loads(raw_path.read_text())
    scoring = json.loads(scoring_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    source_table = json.loads(source_table_path.read_text())
    signal_trace = json.loads(signal_trace_path.read_text())
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
    assert manifest["artifacts"]["source_table"]["path"] == (
        "fund_000001_source_table.json"
    )
    assert manifest["artifacts"]["source_table"]["format"] == "json"
    assert manifest["artifacts"]["signal_trace"]["path"] == (
        "fund_000001_signal_trace.json"
    )
    assert manifest["artifacts"]["signal_trace"]["format"] == "json"
    assert manifest["artifacts"]["markdown"]["path"] == "fund_000001_report.md"
    assert manifest["artifacts"]["html"]["path"] == "fund_000001_report.html"
    assert manifest["provider_foundation"] == scoring["provider_foundation"]
    assert source_table["version"] == "source-table-v1"
    assert source_table["fund_code"] == "000001"
    assert source_table["provider_foundation"] == scoring["provider_foundation"]
    assert source_table["layers"][0]["layer"] == "holdings"
    assert source_table["layers"][0]["display_name"] == "Holdings"
    assert source_table["layers"][0]["source_url"] == "mock://fixtures/fund_000001.json"
    assert source_table["degradation_events"] == scoring["degradation_events"]
    assert signal_trace["version"] == "signal-trace-v1"
    assert signal_trace["fund_code"] == "000001"
    assert signal_trace["provider_foundation"] == scoring["provider_foundation"]
    assert signal_trace["signal_count"] == len(raw["signal_events"])
    primary_trace = signal_trace["narratives"][0]
    assert primary_trace["narrative_id"] == scoring["primary_narrative"]["narrative_id"]
    assert primary_trace["dimensions"][0]["dimension"] == "earnings_score"
    assert primary_trace["dimensions"][0]["score"] == scoring["primary_narrative"][
        "state"
    ]["dimensions"]["earnings_score"]["score"]
    assert any(
        item["source_url"] == "mock://fixtures/signal_events.json"
        for dimension in primary_trace["dimensions"]
        for item in dimension["signals"]
    )
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


def test_artifact_contracts_reject_source_table_identity_mismatch(tmp_path):
    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
    )
    source_table = json.loads(artifacts["source_table"].read_text())
    source_table["fund_code"] = "999999"
    artifacts["source_table"].write_text(
        json.dumps(source_table, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    command = [
        sys.executable,
        "-m",
        "src.main",
        "--validate-artifact-contracts",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "source_table fund_code mismatch" in result.stderr


def test_artifact_contracts_reject_source_table_as_of_date_mismatch(tmp_path):
    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
    )
    source_table = json.loads(artifacts["source_table"].read_text())
    source_table["as_of_date"] = "1900-01-01"
    artifacts["source_table"].write_text(
        json.dumps(source_table, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        main_module._validate_artifact_contracts(tmp_path)
    except ValueError as exc:
        assert "source_table as_of_date mismatch" in str(exc)
    else:
        raise AssertionError("expected source_table as_of_date mismatch")


def test_artifact_contracts_reject_signal_trace_identity_mismatch(tmp_path):
    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
    )
    signal_trace = json.loads(artifacts["signal_trace"].read_text())
    signal_trace["fund_code"] = "999999"
    artifacts["signal_trace"].write_text(
        json.dumps(signal_trace, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        main_module._validate_artifact_contracts(tmp_path)

    assert "signal_trace fund_code mismatch" in str(exc.value)


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
    assert len(raw["derived_signal_events"]) == 2
    assert raw["derived_signal_events"] == scoring["derived_signal_events"]
    assert all(
        item["source"] == "cninfo_announcement"
        for item in raw["derived_signal_events"]
    )
    assert any(
        item["signal_id"].startswith("SIG_ANN_")
        for item in raw["signal_events"]
    )
    assert scoring["provider_foundation"]["layers"]["derived_signals"][
        "provider_name"
    ] == "cninfo-derived-signals"
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


def test_cli_include_market_quotes_passes_options_to_pipeline(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-market-quotes",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["fund_code"] == "161725"
    assert captured["include_market_quotes"] is True


def test_cli_include_valuation_snapshots_requires_market_quotes(capsys):
    with pytest.raises(SystemExit) as exc:
        main_module.main(["--fund-code", "161725", "--include-valuation-snapshots"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "--include-valuation-snapshots requires --include-market-quotes" in captured.err


def test_cli_eastmoney_valuation_source_does_not_require_market_quotes(
    tmp_path,
    monkeypatch,
):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "source_table": tmp_path / "source_table.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--include-valuation-snapshots",
            "--valuation-source",
            "eastmoney",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["include_valuation_snapshots"] is True
    assert captured["valuation_snapshot_source"] == "eastmoney"


def test_cli_include_valuation_snapshots_passes_option_to_pipeline(
    tmp_path,
    monkeypatch,
):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "source_table": tmp_path / "source_table.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-market-quotes",
            "--include-valuation-snapshots",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["include_market_quotes"] is True
    assert captured["include_valuation_snapshots"] is True
    assert captured["valuation_snapshot_source"] == "quote-derived"


def test_cli_include_news_evidence_passes_option_to_pipeline(
    tmp_path,
    monkeypatch,
):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "source_table": tmp_path / "source_table.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-news-evidence",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["include_news_evidence"] is True


def test_cli_include_financial_metrics_passes_option_to_pipeline(
    tmp_path,
    monkeypatch,
):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "source_table": tmp_path / "source_table.json",
            "signal_trace": tmp_path / "signal_trace.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-financial-metrics",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["include_financial_metrics"] is True


def test_cli_base_intelligence_mode_passes_option_to_pipeline(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--include-cninfo-announcements",
            "--base-intelligence-mode",
            "provider-derived",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["base_intelligence_mode"] == "provider-derived"


def test_cli_stock_mapping_mode_passes_option_to_pipeline(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--stock-mapping-mode",
            "registry-rule",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["fund_code"] == "161725"
    assert captured["stock_mapping_mode"] == "registry-rule"


def test_cli_reviewed_stock_mapping_mode_passes_options_to_pipeline(
    tmp_path, monkeypatch
):
    captured = {}
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    mappings_path.write_text(
        (FIXTURE_DIR / "stock_narrative_mappings.json")
        .read_text(encoding="utf-8")
        .replace('"method": "fixture_rule"', '"method": "reviewed_mapping"'),
        encoding="utf-8",
    )

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--stock-mapping-mode",
            "reviewed",
            "--stock-mappings-path",
            str(mappings_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["stock_mapping_mode"] == "reviewed"
    assert captured["stock_mappings_path"] == mappings_path


def test_cli_narrative_registry_mode_passes_options_to_pipeline(tmp_path, monkeypatch):
    captured = {}
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--narrative-registry-mode",
            "reviewed",
            "--narrative-registry-path",
            str(registry_path),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["narrative_registry_mode"] == "reviewed"
    assert captured["narrative_registry_path"] == registry_path


def test_provider_derived_intelligence_excludes_fixture_evidence_and_signals(
    tmp_path,
):
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
            del stock_codes
            del as_of_date
            del start_date
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
        base_intelligence_mode="provider-derived",
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()

    foundation = scoring["provider_foundation"]
    evidence_layer = foundation["layers"]["evidence"]
    signals_layer = foundation["layers"]["signals"]

    assert raw["base_intelligence_mode"] == "provider-derived"
    assert scoring["base_intelligence_mode"] == "provider-derived"
    assert raw["evidence"] == raw["announcement_evidence"]["evidence"]
    assert all(item["source"] == "cninfo_announcement" for item in raw["evidence"])
    assert raw["signal_events"] == raw["derived_signal_events"]
    assert raw["signal_events"] == scoring["derived_signal_events"]
    assert all(item["source"] == "cninfo_announcement" for item in raw["signal_events"])
    assert evidence_layer["provider_name"] == "provider-derived-evidence"
    assert evidence_layer["data_quality"] == "fresh"
    assert evidence_layer["is_mock"] is False
    assert signals_layer["provider_name"] == "provider-derived-signals"
    assert signals_layer["data_quality"] == "fresh"
    assert signals_layer["is_mock"] is False
    assert "Evidence 来自 provider-derived-evidence" in markdown
    assert "Signals 来自 provider-derived-signals" in markdown
    assert "Mock fixtures" in markdown


def test_provider_derived_intelligence_requires_announcements(tmp_path):
    try:
        run_pipeline(
            fund_code="000001",
            provider_mode="mock",
            output_dir=tmp_path,
            base_intelligence_mode="provider-derived",
        )
    except ValueError as exc:
        assert "base_intelligence_mode=provider-derived requires" in str(exc)
    else:
        raise AssertionError("expected ValueError for provider-derived without announcements")


def test_provider_derived_intelligence_preserves_fresh_empty_signal_provenance(
    tmp_path,
):
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
            del stock_codes
            del as_of_date
            del start_date
            return {
                "version": self.provider_version,
                "data_quality": "fresh",
                "announcements": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "title": "2026年度普通公告",
                        "category": "其他",
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
        base_intelligence_mode="provider-derived",
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    signals_layer = scoring["provider_foundation"]["layers"]["signals"]

    assert raw["announcement_evidence"]["data_quality"] == "fresh"
    assert raw.get("derived_signal_events", []) == []
    assert scoring.get("derived_signal_events", []) == []
    assert raw["signal_events"] == []
    assert signals_layer["provider_name"] == "provider-derived-signals"
    assert signals_layer["data_quality"] == "unavailable"
    assert "source providers: none" in signals_layer["note"]
    assert "derived_signals" not in scoring["provider_foundation"]["layers"]


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


def test_optional_eastmoney_quotes_are_disclosed_and_added_to_outputs(tmp_path):
    class FakeMarketDataProvider:
        provider_name = "eastmoney-market-quote"
        provider_version = "eastmoney-market-quote-v1"
        source_url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        degradation_events: list[dict[str, str]] = []

        def get_stock_quotes(self, stock_codes: list[str]) -> dict:
            assert "NVDA" in stock_codes
            return {
                "version": self.provider_version,
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "quotes": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "latest_price": 1000.0,
                        "change_percent": 1.5,
                        "change_amount": 14.7,
                        "volume": 100,
                        "amount": 100000.0,
                        "high": 1005.0,
                        "low": 990.0,
                        "open": 995.0,
                        "previous_close": 985.3,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                    }
                ],
                "missing_stock_codes": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_market_quotes=True,
        market_data_provider=FakeMarketDataProvider(),
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()

    quote_layer = scoring["provider_foundation"]["layers"]["market_quotes"]

    assert raw["market_quotes"] == scoring["market_quotes"]
    assert raw["market_quotes"]["data_quality"] == "fresh"
    assert raw["market_quotes"]["quotes"][0]["stock_code"] == "NVDA"
    assert len(raw["derived_signal_events"]) >= 1
    assert raw["derived_signal_events"] == scoring["derived_signal_events"]
    assert all(item["source"] == "market_quote" for item in raw["derived_signal_events"])
    assert all(
        item["signal_type"] == "relative_strength_up"
        for item in raw["derived_signal_events"]
    )
    assert set(item["signal_id"] for item in raw["derived_signal_events"]).issubset({
        item["signal_id"] for item in raw["signal_events"]
    })
    assert scoring["provider_foundation"]["layers"]["derived_signals"][
        "provider_name"
    ] == "market-quote-derived-signals"
    assert scoring["metadata"]["data_quality"] == "partial"
    assert quote_layer["provider_name"] == "eastmoney-market-quote"
    assert quote_layer["data_quality"] == "fresh"
    assert quote_layer["is_mock"] is False
    assert "Market Quotes" in markdown
    assert "eastmoney-market-quote" in markdown
    assert "Market Quotes" in html
    assert "eastmoney-market-quote" in html


def test_optional_valuation_snapshots_are_quote_derived_and_disclosed(tmp_path):
    class FakeMarketDataProvider:
        provider_name = "eastmoney-market-quote"
        provider_version = "eastmoney-market-quote-v1"
        source_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        degradation_events: list[dict[str, str]] = []

        def get_stock_quotes(self, stock_codes: list[str]) -> dict:
            assert "NVDA" in stock_codes
            return {
                "version": self.provider_version,
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "quotes": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "source_provider": "eastmoney",
                        "source_url": self.source_url,
                        "latest_price": 106.0,
                        "change_percent": 6.0,
                        "change_amount": 6.0,
                        "volume": 100,
                        "amount": 10600.0,
                        "high": 107.0,
                        "low": 99.0,
                        "open": 100.0,
                        "previous_close": 100.0,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                    }
                ],
                "missing_stock_codes": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_market_quotes=True,
        include_valuation_snapshots=True,
        market_data_provider=FakeMarketDataProvider(),
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    source_table = json.loads(artifacts["source_table"].read_text())
    valuation = raw["valuation_snapshots"]
    valuation_layer = scoring["provider_foundation"]["layers"]["valuation"]

    assert valuation == scoring["valuation_snapshots"]
    assert valuation["provider_name"] == "quote-derived-valuation"
    assert valuation["valuation_basis"] == "quote_derived_context"
    assert valuation["valuations"][0]["valuation_pressure"] == "elevated"
    assert valuation["valuations"][0]["source"] == "market_quote"
    assert valuation["valuations"][0]["source_provider"] == "eastmoney"
    assert valuation["valuations"][0]["source_url"] == FakeMarketDataProvider.source_url
    assert valuation_layer["provider_name"] == "quote-derived-valuation"
    assert valuation_layer["is_mock"] is False
    assert {layer["layer"] for layer in source_table["layers"]} >= {"valuation"}
    assert "Quote-derived valuation context" in artifacts["markdown"].read_text()
    assert "not a full fundamental valuation feed" in artifacts["html"].read_text()


def test_optional_valuation_snapshots_can_use_eastmoney_metrics(tmp_path):
    class FakeValuationProvider:
        provider_name = "eastmoney-valuation"
        provider_version = "eastmoney-valuation-v1"
        source_url = "https://push2.eastmoney.com/api/qt/stock/get"
        degradation_events: list[dict[str, str]] = []

        def get_valuation_snapshots(self, stock_codes: list[str]) -> dict:
            assert "NVDA" in stock_codes
            return {
                "version": "valuation-snapshot-v1",
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "valuation_basis": "provider_valuation_metrics",
                "valuations": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "latest_price": 106.0,
                        "previous_close": 100.0,
                        "price_change_percent": 6.0,
                        "valuation_pressure": "elevated",
                        "source": "provider_valuation_metrics",
                        "source_provider": self.provider_name,
                        "source_url": self.source_url,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                        "pe_ttm": 54.2,
                        "pb": 18.0,
                        "market_cap": 2_600_000_000_000.0,
                        "float_market_cap": 2_590_000_000_000.0,
                        "turnover_rate": 1.2,
                    }
                ],
                "missing_stock_codes": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_valuation_snapshots=True,
        valuation_snapshot_source="eastmoney",
        valuation_provider=FakeValuationProvider(),
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    source_table = json.loads(artifacts["source_table"].read_text())
    valuation = raw["valuation_snapshots"]
    valuation_layer = scoring["provider_foundation"]["layers"]["valuation"]
    valuation_signals = [
        item
        for item in raw["derived_signal_events"]
        if item["source"] == "valuation_snapshot"
        and item["narrative_id"] == "N_AI_INFRA"
    ]

    assert valuation == scoring["valuation_snapshots"]
    assert raw["derived_signal_events"] == scoring["derived_signal_events"]
    assert valuation["provider_name"] == "eastmoney-valuation"
    assert valuation["valuation_basis"] == "provider_valuation_metrics"
    assert valuation["valuations"][0]["pe_ttm"] == 54.2
    assert valuation["valuations"][0]["source"] == "provider_valuation_metrics"
    assert valuation_signals == [
        {
            "signal_id": "SIG_VAL_NVDA_N_AI_INFRA_VALUATION_EXTREME",
            "narrative_id": "N_AI_INFRA",
            "signal_type": "valuation_extreme",
            "strength": 1.0,
            "confidence": 0.645,
            "confidence_multiplier": 0.75,
            "event_date": "2026-05-14",
            "half_life_days": 30,
            "source": "valuation_snapshot",
            "source_provider": "eastmoney-valuation",
            "source_stock_code": "NVDA",
            "source_url": "https://push2.eastmoney.com/api/qt/stock/get",
            "derivation_reason": "elevated provider valuation metrics",
        }
    ]
    assert any(
        item["signal_type"] == "valuation_extreme" for item in raw["signal_events"]
    )
    assert scoring["primary_narrative"]["state"]["dimensions"][
        "valuation_risk_score"
    ]["score"] > 60
    assert valuation_layer["provider_name"] == "eastmoney-valuation"
    assert valuation_layer["is_mock"] is False
    assert {layer["layer"] for layer in source_table["layers"]} >= {"valuation"}
    assert "Eastmoney valuation metrics" in artifacts["markdown"].read_text()


def test_optional_financial_metrics_produce_earnings_signals(tmp_path):
    class FakeFinancialMetricsProvider:
        provider_name = "eastmoney-financial-metrics"
        provider_version = "eastmoney-financial-metrics-v1"
        source_url = "https://datacenter.eastmoney.com/securities/api/data/get"
        degradation_events: list[dict[str, str]] = []

        def get_financial_metrics(self, stock_codes: list[str]) -> dict:
            assert "NVDA" in stock_codes
            return {
                "version": "financial-metrics-v1",
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-15T00:00:00+00:00",
                "metrics": [
                    {
                        "stock_code": "NVDA",
                        "stock_name": "NVIDIA",
                        "report_date": "2026-03-31",
                        "report_type": "一季报",
                        "notice_date": "2026-04-25",
                        "currency": "USD",
                        "revenue": 26_000_000_000.0,
                        "revenue_yoy": 18.0,
                        "parent_net_profit": 14_000_000_000.0,
                        "parent_net_profit_yoy": 22.0,
                        "deduct_parent_net_profit_yoy": 21.0,
                        "roe": 32.0,
                        "gross_margin": 72.0,
                        "net_margin": 54.0,
                        "debt_asset_ratio": 18.0,
                        "source": "provider_financial_metrics",
                        "source_provider": self.provider_name,
                        "source_url": self.source_url,
                        "retrieved_at": "2026-05-15T00:00:00+00:00",
                    }
                ],
                "missing_stock_codes": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_financial_metrics=True,
        financial_metrics_provider=FakeFinancialMetricsProvider(),
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    signal_trace = json.loads(artifacts["signal_trace"].read_text())
    financial_layer = scoring["provider_foundation"]["layers"]["financial_metrics"]
    financial_signals = [
        item
        for item in raw["derived_signal_events"]
        if item["source"] == "financial_metrics"
        and item["narrative_id"] == "N_AI_INFRA"
    ]

    assert raw["financial_metrics"] == scoring["financial_metrics"]
    assert raw["financial_metrics"]["provider_name"] == "eastmoney-financial-metrics"
    assert financial_layer["provider_name"] == "eastmoney-financial-metrics"
    assert financial_layer["is_mock"] is False
    assert financial_signals[0]["signal_type"] == "revenue_growth_up"
    assert any(
        signal["source_layer"] == "financial_metrics"
        for narrative in signal_trace["narratives"]
        for dimension in narrative["dimensions"]
        for signal in dimension["signals"]
    )
    assert scoring["primary_narrative"]["state"]["dimensions"]["earnings_score"][
        "score"
    ] > 50


def test_optional_news_evidence_is_disclosed_and_added_to_outputs(tmp_path):
    class FakeNewsEvidenceProvider:
        provider_name = "google-news-rss"
        provider_version = "google-news-rss-v1"
        source_url = "https://news.google.com/rss/search"

        def get_news_evidence(self, narratives: list[dict], as_of_date: str) -> dict:
            assert as_of_date == "2026-05-13"
            assert narratives[0]["narrative_id"] == "N_AI_INFRA"
            return {
                "version": "news-evidence-v1",
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "query_scope": {
                    "requested_narrative_ids": [],
                    "queried_narrative_ids": [
                        narrative["narrative_id"] for narrative in narratives
                    ],
                    "omitted_narrative_ids": [],
                    "query_limit": 4,
                },
                "evidence": [
                    {
                        "evidence_id": "EV_NEWS_N_AI_INFRA_TEST",
                        "narrative_id": "N_AI_INFRA",
                        "type": "news",
                        "source": "google_news_rss",
                        "source_url": "https://example.com/news/ai",
                        "title": "AI infrastructure growth accelerates",
                        "summary": (
                            "Example News headline/snippet matched the narrative "
                            "query. V1 classified only RSS title/snippet text; "
                            "article body content was not parsed."
                        ),
                        "sentiment": "positive",
                        "confidence": 0.52,
                        "event_date": "2026-05-14",
                        "source_provider": self.provider_name,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                        "provider_data_quality": "fresh",
                        "classification_reason": "keyword heuristic over RSS title/snippet",
                    }
                ],
                "missing_narrative_ids": [],
                "skipped_item_count": 0,
                "degradation_events": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_news_evidence=True,
        news_evidence_provider=FakeNewsEvidenceProvider(),
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    source_table = json.loads(artifacts["source_table"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()
    news_layer = scoring["provider_foundation"]["layers"]["news_evidence"]

    assert raw["news_evidence"] == scoring["news_evidence"]
    assert raw["news_evidence"]["provider_name"] == "google-news-rss"
    assert raw["news_evidence"]["query_scope"]["requested_narrative_ids"] == sorted(
        item["narrative_id"] for item in scoring["all_narratives"]
    )
    assert raw["news_evidence"]["query_scope"]["omitted_narrative_ids"] == []
    assert raw["news_evidence"]["evidence"][0]["source"] == "google_news_rss"
    assert any(item["source"] == "google_news_rss" for item in raw["evidence"])
    assert raw["derived_signal_events"] == scoring["derived_signal_events"]
    assert any(item["source"] == "news_evidence" for item in raw["derived_signal_events"])
    assert any(item["signal_type"] == "news_frequency_up" for item in raw["signal_events"])
    assert scoring["provider_foundation"]["layers"]["derived_signals"][
        "provider_name"
    ] == "news-derived-signals"
    assert news_layer["provider_name"] == "google-news-rss"
    assert news_layer["is_mock"] is False
    assert "titles/snippets only" in news_layer["note"]
    assert "queried 4/4 mapped narratives" in news_layer["note"]
    assert {layer["layer"] for layer in source_table["layers"]} >= {"news_evidence"}
    assert "News Evidence" in markdown
    assert "titles/snippets only" in html


def test_provider_derived_mode_uses_news_evidence_and_signals(tmp_path):
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
            del stock_codes, as_of_date, start_date
            return {
                "version": self.provider_version,
                "data_quality": "fresh",
                "announcements": [],
                "missing_stock_codes": [],
            }

    class FakeNewsEvidenceProvider:
        provider_name = "google-news-rss"
        provider_version = "google-news-rss-v1"
        source_url = "https://news.google.com/rss/search"

        def get_news_evidence(self, narratives: list[dict], as_of_date: str) -> dict:
            del as_of_date
            return {
                "version": "news-evidence-v1",
                "provider_name": self.provider_name,
                "provider_version": self.provider_version,
                "data_quality": "fresh",
                "source_url": self.source_url,
                "retrieved_at": "2026-05-14T00:00:00+00:00",
                "query_scope": {
                    "requested_narrative_ids": [],
                    "queried_narrative_ids": [
                        narrative["narrative_id"] for narrative in narratives
                    ],
                    "omitted_narrative_ids": [],
                    "query_limit": 4,
                },
                "evidence": [
                    {
                        "evidence_id": "EV_NEWS_N_AI_INFRA_TEST",
                        "narrative_id": "N_AI_INFRA",
                        "type": "news",
                        "source": "google_news_rss",
                        "source_url": "https://example.com/news/ai",
                        "title": "AI infrastructure growth accelerates",
                        "summary": (
                            "Example News headline/snippet matched the narrative "
                            "query. V1 classified only RSS title/snippet text; "
                            "article body content was not parsed."
                        ),
                        "sentiment": "positive",
                        "confidence": 0.52,
                        "event_date": "2026-05-14",
                        "source_provider": self.provider_name,
                        "retrieved_at": "2026-05-14T00:00:00+00:00",
                        "provider_data_quality": "fresh",
                        "classification_reason": "keyword heuristic over RSS title/snippet",
                    }
                ],
                "missing_narrative_ids": [],
                "skipped_item_count": 0,
                "degradation_events": [],
            }

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        include_announcement_evidence=True,
        announcement_provider=FakeAnnouncementProvider(),
        include_news_evidence=True,
        news_evidence_provider=FakeNewsEvidenceProvider(),
        base_intelligence_mode="provider-derived",
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    foundation = scoring["provider_foundation"]

    assert raw["base_intelligence_mode"] == "provider-derived"
    assert raw["evidence"] == raw["news_evidence"]["evidence"]
    assert raw["signal_events"] == raw["derived_signal_events"]
    assert raw["signal_events"][0]["source"] == "news_evidence"
    assert foundation["layers"]["evidence"]["provider_name"] == (
        "provider-derived-evidence"
    )
    assert "news_evidence" in foundation["layers"]["evidence"]["note"]
    assert foundation["layers"]["signals"]["provider_name"] == (
        "provider-derived-signals"
    )
    assert foundation["layers"]["derived_signals"]["provider_name"] == (
        "news-derived-signals"
    )


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


def test_registry_rule_stock_mapping_mode_uses_runtime_mapping_layer(
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
        stock_mapping_mode="registry-rule",
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()

    mapping_layer = scoring["provider_foundation"]["layers"]["stock_mappings"]

    assert raw["stock_mapping_mode"] == "registry-rule"
    assert scoring["stock_mapping_mode"] == "registry-rule"
    assert raw["mapping_coverage"]["mapping_methods"] == {"registry_term_rule": 2}
    assert all(
        mapping["method"] == "registry_term_rule"
        for mapping in raw["stock_narrative_mappings"]
    )
    assert {mapping["stock_code"] for mapping in raw["stock_narrative_mappings"]} == {
        "600519",
        "000858",
    }
    assert mapping_layer["provider_name"] == "registry-rule-stock-mapping"
    assert mapping_layer["data_quality"] == "partial"
    assert mapping_layer["source_url"] == "derived://registry-term-rule-stock-mapping"
    assert mapping_layer["is_mock"] is False
    assert scoring["provider_foundation"]["layers"]["narrative_registry"][
        "is_mock"
    ] is True
    assert "Stock Mappings 来自 registry-rule-stock-mapping" in markdown
    assert "Narrative Registry" in markdown
    assert "Mock fixtures" in markdown


def test_reviewed_narrative_registry_mode_uses_store_layer(tmp_path):
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text(_reviewed_registry_text(), encoding="utf-8")

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        narrative_registry_mode="reviewed",
        narrative_registry_path=registry_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()
    html = artifacts["html"].read_text()
    registry_layer = scoring["provider_foundation"]["layers"]["narrative_registry"]

    assert raw["narrative_registry_mode"] == "reviewed"
    assert scoring["narrative_registry_mode"] == "reviewed"
    assert registry_layer["provider_name"] == "reviewed-registry-store"
    assert registry_layer["data_quality"] == "fresh"
    assert registry_layer["source_url"].startswith("reviewed-registry://external/")
    assert "/narrative_registry.reviewed.json#sha256=" in registry_layer["source_url"]
    assert registry_layer["is_mock"] is False
    assert registry_layer["review_metadata"]["reviewed_by"] == "seed-curation"
    assert scoring["provider_foundation"]["effective_data_quality"] == "partial"
    assert "Narrative Registry 来自 reviewed-registry-store" in markdown
    assert "reviewed-registry://external/" in markdown
    assert "Narrative Registry 来自 reviewed-registry-store" in html


def test_reviewed_stock_mapping_mode_uses_store_layer(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    mappings_path.write_text(_reviewed_mapping_text(), encoding="utf-8")

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        stock_mapping_mode="reviewed",
        stock_mappings_path=mappings_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    review_queue = json.loads(artifacts["review_queue"].read_text())
    source_table = json.loads(artifacts["source_table"].read_text())
    manifest = json.loads(artifacts["manifest"].read_text())
    markdown = artifacts["markdown"].read_text()
    mapping_layer = scoring["provider_foundation"]["layers"]["stock_mappings"]

    assert raw["stock_mapping_mode"] == "reviewed"
    assert scoring["stock_mapping_mode"] == "reviewed"
    assert all(
        mapping["method"] == "reviewed_mapping"
        for mapping in raw["stock_narrative_mappings"]
    )
    assert mapping_layer["provider_name"] == "reviewed-mapping-store"
    assert mapping_layer["data_quality"] == "partial"
    assert mapping_layer["is_mock"] is False
    assert mapping_layer["source_url"].startswith("reviewed-mapping://external/")
    assert mapping_layer["review_metadata"]["reviewed_by"] == "seed-curation"
    assert raw["provider_foundation"] == scoring["provider_foundation"]
    assert review_queue["provider_foundation"] == scoring["provider_foundation"]
    assert source_table["provider_foundation"] == scoring["provider_foundation"]
    assert {layer["layer"]: layer for layer in source_table["layers"]} == {
        layer["layer"]: layer
        for layer in scoring["provider_foundation"]["layers"].values()
    }
    assert {layer["layer"]: layer for layer in source_table["layers"]}[
        "stock_mappings"
    ]["review_metadata"]["reviewed_by"] == (
        "seed-curation"
    )
    assert manifest["provider_foundation"] == scoring["provider_foundation"]
    assert "Stock Mappings 来自 reviewed-mapping-store" in markdown


def test_reviewed_stock_mapping_mode_does_not_fallback_to_registry_rule(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    mappings_path.write_text(
        json.dumps(
            {
                "version": "mapping-v1",
                "review_metadata": _review_metadata(),
                "mappings": [
                    {
                        "stock_code": "NVDA",
                        "narrative_id": "N_AI_INFRA",
                        "mapping_weight": 0.9,
                        "confidence": 0.86,
                        "method": "reviewed_mapping",
                        "review": _review_entry(),
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        stock_mapping_mode="reviewed",
        stock_mappings_path=mappings_path,
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())

    assert raw["mapping_coverage"]["mapping_methods"] == {"reviewed_mapping": 1}
    assert all(
        mapping["method"] == "reviewed_mapping"
        for mapping in raw["stock_narrative_mappings"]
    )
    assert raw["mapping_coverage"]["covered_holding_count"] == 1
    assert raw["unmapped_holdings"]
    assert scoring["provider_foundation"]["layers"]["stock_mappings"][
        "provider_name"
    ] == "reviewed-mapping-store"


def test_registry_rule_mapping_keeps_fully_mock_run_mock(tmp_path):
    artifacts = run_pipeline(
        fund_code="000001",
        provider_mode="mock",
        output_dir=tmp_path,
        stock_mapping_mode="registry-rule",
    )

    raw = json.loads(artifacts["raw"].read_text())
    scoring = json.loads(artifacts["scoring"].read_text())
    markdown = artifacts["markdown"].read_text()

    mapping_layer = scoring["provider_foundation"]["layers"]["stock_mappings"]

    assert raw["metadata"]["data_quality"] == "mock"
    assert scoring["metadata"]["data_quality"] == "mock"
    assert scoring["provider_foundation"]["effective_data_quality"] == "mock"
    assert mapping_layer["provider_name"] == "registry-rule-stock-mapping"
    assert mapping_layer["data_quality"] == "mock"
    assert mapping_layer["is_mock"] is True
    assert "Mock 数据" in markdown
    assert "混合数据源" not in markdown


def test_cli_rejects_stock_mapping_mode_with_provider_diagnostics(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--provider-diagnostics",
        "--stock-mapping-mode",
        "registry-rule",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--stock-mapping-mode is only supported" in result.stderr
    assert not list(tmp_path.glob("*"))


def test_cli_rejects_stock_mapping_mode_with_batch_actions(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--run-real-smoke",
        "--stock-mapping-mode",
        "registry-rule",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--stock-mapping-mode is only supported" in result.stderr
    assert not list(tmp_path.glob("*"))


def test_cli_rejects_stock_mapping_mode_with_validation_actions(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--validate-artifact-contracts",
        str(tmp_path),
        "--stock-mapping-mode",
        "registry-rule",
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--stock-mapping-mode is only supported" in result.stderr


def test_cli_rejects_stock_mapping_mode_with_review_actions(tmp_path):
    action_path = tmp_path / "action.json"
    action_path.write_text("{}", encoding="utf-8")

    exit_code = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.main",
            "--preview-review-action",
            str(action_path),
            "--stock-mapping-mode",
            "registry-rule",
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert exit_code.returncode == 2
    assert "--stock-mapping-mode is only supported" in exit_code.stderr


def test_cli_rejects_narrative_registry_mode_with_provider_diagnostics(tmp_path):
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--provider-diagnostics",
        "--narrative-registry-mode",
        "reviewed",
        "--output-dir",
        str(tmp_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--narrative-registry-mode is only supported" in result.stderr
    assert not list(tmp_path.glob("*"))


def test_cli_rejects_narrative_registry_path_without_reviewed_mode(tmp_path):
    registry_path = tmp_path / "narrative_registry.reviewed.json"
    registry_path.write_text(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--narrative-registry-path",
        str(registry_path),
        "--output-dir",
        str(tmp_path / "out"),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--narrative-registry-path requires --narrative-registry-mode reviewed" in (
        result.stderr
    )
    assert not (tmp_path / "out").exists()


def test_cli_rejects_stock_mappings_path_without_reviewed_mode(tmp_path):
    mappings_path = tmp_path / "stock_narrative_mappings.reviewed.json"
    mappings_path.write_text(
        (FIXTURE_DIR / "stock_narrative_mappings.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        "-m",
        "src.main",
        "--fund-code",
        "000001",
        "--stock-mappings-path",
        str(mappings_path),
        "--output-dir",
        str(tmp_path / "out"),
    ]

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    assert result.returncode == 2
    assert "--stock-mappings-path requires --stock-mapping-mode reviewed" in (
        result.stderr
    )
    assert not (tmp_path / "out").exists()


def test_cli_stock_mapping_mode_still_allows_single_run(tmp_path, monkeypatch):
    captured = {}

    def fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "raw": tmp_path / "raw.json",
            "scoring": tmp_path / "scoring.json",
            "review_queue": tmp_path / "review_queue.json",
            "manifest": tmp_path / "manifest.json",
            "markdown": tmp_path / "report.md",
            "html": tmp_path / "report.html",
        }

    monkeypatch.setattr(main_module, "run_pipeline", fake_run_pipeline)

    exit_code = main_module.main(
        [
            "--fund-code",
            "000001",
            "--stock-mapping-mode",
            "registry-rule",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert captured["stock_mapping_mode"] == "registry-rule"


def test_pipeline_rejects_unknown_stock_mapping_mode(tmp_path):
    try:
        run_pipeline(
            fund_code="000001",
            provider_mode="mock",
            output_dir=tmp_path,
            stock_mapping_mode="unknown",
        )
    except ValueError as exc:
        assert "stock_mapping_mode" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown stock mapping mode")


def test_pipeline_rejects_unknown_narrative_registry_mode(tmp_path):
    try:
        run_pipeline(
            fund_code="000001",
            provider_mode="mock",
            output_dir=tmp_path,
            narrative_registry_mode="unknown",
        )
    except ValueError as exc:
        assert "narrative_registry_mode" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown registry mode")


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


def _review_metadata() -> dict:
    return {
        "review_schema_version": "review-metadata-v1",
        "reviewed_by": "seed-curation",
        "reviewed_at": "2026-05-15",
        "review_note": "Test reviewed store metadata.",
    }


def _review_entry() -> dict:
    return {
        "status": "approved",
        "reviewed_by": "seed-curation",
        "reviewed_at": "2026-05-15",
        "review_note": "Test reviewed entry metadata.",
    }


def _reviewed_registry_text() -> str:
    payload = json.loads((FIXTURE_DIR / "narrative_registry.json").read_text())
    payload["review_metadata"] = _review_metadata()
    for narrative in payload["narratives"]:
        narrative["reviewed_by"] = "seed-curation"
        narrative["reviewed_at"] = "2026-05-15"
    return json.dumps(payload, ensure_ascii=False)


def _reviewed_mapping_text() -> str:
    payload = json.loads((FIXTURE_DIR / "stock_narrative_mappings.json").read_text())
    payload["review_metadata"] = _review_metadata()
    for mapping in payload["mappings"]:
        mapping["method"] = "reviewed_mapping"
        mapping["review"] = _review_entry()
    return json.dumps(payload, ensure_ascii=False)
