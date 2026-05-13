import json
from pathlib import Path

from src.errors import ProviderFetchError
from src.real_fund_smoke import REAL_FUND_SMOKE_SET, run_real_fund_smoke


def test_real_fund_smoke_set_covers_core_scenarios():
    assert [item["fund_code"] for item in REAL_FUND_SMOKE_SET] == [
        "161725",
        "320007",
        "003096",
        "003834",
        "001475",
        "000991",
    ]
    assert {item["scenario"] for item in REAL_FUND_SMOKE_SET} == {
        "baijiu_consumption",
        "semiconductor",
        "healthcare",
        "new_energy",
        "defense",
        "real_estate",
    }


def test_real_fund_smoke_summary_uses_runner_outputs(tmp_path):
    def fake_runner(fund_code: str, provider_mode: str, output_dir: Path):
        scoring_path = output_dir / f"fund_{fund_code}_scoring.json"
        raw_path = output_dir / f"fund_{fund_code}_raw.json"
        markdown_path = output_dir / f"fund_{fund_code}_report.md"
        html_path = output_dir / f"fund_{fund_code}_report.html"
        coverage_ratio = 0.9 if fund_code != "000000" else 0.2
        scoring_path.write_text(
            json.dumps(
                {
                    "metadata": {
                        "fund_code": fund_code,
                        "data_quality": "fresh",
                        "as_of_date": "2026-03-31",
                    },
                    "primary_narrative": {
                        "name": f"Narrative {fund_code}",
                        "state": {
                            "stage": "diverging",
                            "sustainability_score": 50,
                            "confidence": 0.6,
                        },
                    },
                    "mapping_coverage": {
                        "coverage_ratio": coverage_ratio,
                        "covered_holding_count": 9,
                        "total_holding_count": 10,
                        "mapping_methods": {"registry_term_rule": 9},
                    },
                    "unmapped_holdings": [],
                    "degradation_events": [],
                    "provider_foundation": {
                        "effective_data_quality": "partial",
                        "disclosure_required": True,
                        "disclosure_message": "混合数据源：持仓来自 Eastmoney，其余智能层使用 Mock fixtures。",
                    },
                }
            )
        )
        raw_path.write_text("{}")
        markdown_path.write_text("# report")
        html_path.write_text("<html></html>")
        return {
            "raw": raw_path,
            "scoring": scoring_path,
            "markdown": markdown_path,
            "html": html_path,
        }

    summary = run_real_fund_smoke(
        output_dir=tmp_path,
        fund_specs=[{"fund_code": "161725", "scenario": "baijiu_consumption"}],
        runner=fake_runner,
        min_coverage_ratio=0.8,
    )

    assert summary["status"] == "passed"
    assert summary["provider_mode"] == "eastmoney"
    assert summary["min_coverage_ratio"] == 0.8
    assert summary["funds"][0]["fund_code"] == "161725"
    assert summary["funds"][0]["coverage_ratio"] == 0.9
    assert summary["funds"][0]["effective_data_quality"] == "partial"
    assert summary["funds"][0]["data_source_notice_required"] is True
    assert (tmp_path / "real_fund_smoke_summary.json").exists()
    assert (tmp_path / "real_fund_smoke_summary.md").exists()

    summary_markdown = (tmp_path / "real_fund_smoke_summary.md").read_text()
    assert "Data Quality" in summary_markdown
    assert "Notice" in summary_markdown
    assert "partial" in summary_markdown


def test_real_fund_smoke_summary_fails_when_coverage_is_below_threshold(tmp_path):
    def fake_runner(fund_code: str, provider_mode: str, output_dir: Path):
        scoring_path = output_dir / f"fund_{fund_code}_scoring.json"
        scoring_path.write_text(
            json.dumps(
                {
                    "metadata": {
                        "fund_code": fund_code,
                        "data_quality": "fresh",
                        "as_of_date": "2026-03-31",
                    },
                    "primary_narrative": {
                        "name": "Thin Coverage",
                        "state": {
                            "stage": "diverging",
                            "sustainability_score": 50,
                            "confidence": 0.6,
                        },
                    },
                    "mapping_coverage": {
                        "coverage_ratio": 0.4,
                        "covered_holding_count": 4,
                        "total_holding_count": 10,
                        "mapping_methods": {"registry_term_rule": 4},
                    },
                    "unmapped_holdings": [
                        {"stock_code": "UNKNOWN", "stock_name": "Unknown"}
                    ],
                    "degradation_events": [],
                }
            )
        )
        return {"scoring": scoring_path}

    summary = run_real_fund_smoke(
        output_dir=tmp_path,
        fund_specs=[{"fund_code": "000000", "scenario": "thin"}],
        runner=fake_runner,
        min_coverage_ratio=0.8,
    )

    assert summary["status"] == "failed"
    assert summary["funds"][0]["coverage_passed"] is False


def test_real_fund_smoke_summary_records_runner_failures(tmp_path):
    def failing_runner(fund_code: str, provider_mode: str, output_dir: Path):
        raise ProviderFetchError(f"temporary provider failure for {fund_code}")

    summary = run_real_fund_smoke(
        output_dir=tmp_path,
        fund_specs=[{"fund_code": "161725", "scenario": "baijiu_consumption"}],
        runner=failing_runner,
        min_coverage_ratio=0.8,
    )

    assert summary["status"] == "failed"
    assert summary["funds"][0]["status"] == "failed"
    assert summary["funds"][0]["coverage_passed"] is False
    assert summary["funds"][0]["primary_narrative"] is None
    assert "temporary provider failure" in summary["funds"][0]["error"]
    assert (tmp_path / "real_fund_smoke_summary.json").exists()
    assert (tmp_path / "real_fund_smoke_summary.md").exists()
