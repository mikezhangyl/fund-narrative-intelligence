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
                    "unmapped_holdings": [
                        {
                            "stock_code": "002572",
                            "stock_name": "索菲亚",
                            "industry": "轻工制造",
                            "weight": 0.0403,
                        }
                    ],
                    "mapping_precision_flags": [
                        {
                            "type": "broad_industry_fallback",
                            "severity": "watch",
                            "stock_code": "600522",
                            "stock_name": "中天科技",
                            "industry": "通信",
                            "weight": 0.042,
                            "mapping_method": "registry_term_rule",
                            "narrative_ids": ["N_SEMI_CAPEX"],
                            "narratives": ["Semiconductor Capex Cycle"],
                            "confidence_before": 0.52,
                            "confidence_after": 0.48,
                            "recommended_action": "curation_review",
                        }
                    ],
                    "excluded_mapping_candidates": [
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
                                "Consumer electronics device exposure is too "
                                "broad for Semiconductor Capex."
                            ),
                            "recommended_action": "candidate_narrative_review",
                        }
                    ],
                    "candidate_narratives": [
                        {
                            "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
                            "name": "Consumer Electronics Globalization",
                            "canonical_taxonomy": "Technology Hardware",
                            "status": "candidate",
                            "source": "mapping_exclusion_review",
                            "triggering_stock_codes": ["688036"],
                            "related_exclusion_ids": ["EX_SEMI_688036"],
                            "aliases": ["consumer electronics exports"],
                            "related_terms": ["消费电子"],
                            "rationale": (
                                "Device exposure candidate, not semiconductor capex."
                            ),
                            "human_review_status": "candidate",
                            "reviewed_by": None,
                            "reviewed_at": None,
                            "first_seen_at": "2026-05-14",
                            "last_updated_at": "2026-05-14",
                        }
                    ],
                    "candidate_review_queue": {
                        "version": "candidate-review-queue-v1",
                        "summary": {
                            "total_count": 1,
                            "pending_count": 1,
                            "action_required": True,
                        },
                        "items": [
                            {
                                "review_item_id": (
                                    "RQ_C_CONSUMER_ELECTRONICS_GLOBALIZATION"
                                ),
                                "item_type": "candidate_narrative",
                                "candidate_narrative_id": (
                                    "C_CONSUMER_ELECTRONICS_GLOBALIZATION"
                                ),
                                "name": "Consumer Electronics Globalization",
                                "canonical_taxonomy": "Technology Hardware",
                                "status": "candidate",
                                "human_review_status": "candidate",
                                "source": "mapping_exclusion_review",
                                "rationale": (
                                    "Device exposure candidate, not semiconductor capex."
                                ),
                                "triggering_stock_codes": ["688036"],
                                "related_exclusion_ids": ["EX_SEMI_688036"],
                                "related_exclusions": [],
                                "available_actions": ["approve", "reject", "defer"],
                                "default_action": "defer",
                                "requires_promotion_metadata": True,
                                "promotion_action_template": {},
                            }
                        ],
                    },
                    "degradation_events": [],
                    "provider_foundation": {
                        "effective_data_quality": "partial",
                        "disclosure_required": True,
                        "disclosure_message": "混合数据源：持仓来自 Eastmoney，其余智能层使用 Mock fixtures。",
                    },
                }
            )
        )
        raw_path.write_text(
            json.dumps(
                {
                    "holdings": [
                        {
                            "stock_code": "000001",
                            "stock_name": "Multi Co",
                            "industry": "测试行业",
                            "weight": 0.05,
                        }
                    ],
                    "stock_narrative_mappings": [
                        {
                            "stock_code": "000001",
                            "narrative_id": "N_ONE",
                            "method": "registry_term_rule",
                        },
                        {
                            "stock_code": "000001",
                            "narrative_id": "N_TWO",
                            "method": "registry_term_rule",
                        },
                    ],
                    "narrative_registry": [
                        {"narrative_id": "N_ONE", "name": "Narrative One"},
                        {"narrative_id": "N_TWO", "name": "Narrative Two"},
                    ],
                }
            ),
            encoding="utf-8",
        )
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
    assert summary["funds"][0]["unmapped_holding_count"] == 1
    assert summary["funds"][0]["unmapped_holdings"] == [
        {
            "stock_code": "002572",
            "stock_name": "索菲亚",
            "industry": "轻工制造",
            "weight": 0.0403,
        }
    ]
    assert summary["funds"][0]["multi_mapped_holding_count"] == 1
    assert summary["funds"][0]["multi_mapped_holdings"] == [
        {
            "stock_code": "000001",
            "stock_name": "Multi Co",
            "industry": "测试行业",
            "weight": 0.05,
            "narratives": ["Narrative One", "Narrative Two"],
            "narrative_ids": ["N_ONE", "N_TWO"],
            "methods": ["registry_term_rule"],
        }
    ]
    assert summary["funds"][0]["mapping_precision_flag_count"] == 1
    assert summary["funds"][0]["mapping_precision_flags"] == [
        {
            "type": "broad_industry_fallback",
            "severity": "watch",
            "stock_code": "600522",
            "stock_name": "中天科技",
            "industry": "通信",
            "weight": 0.042,
            "mapping_method": "registry_term_rule",
            "narrative_ids": ["N_SEMI_CAPEX"],
            "narratives": ["Semiconductor Capex Cycle"],
            "confidence_before": 0.52,
            "confidence_after": 0.48,
            "recommended_action": "curation_review",
        }
    ]
    assert summary["funds"][0]["excluded_mapping_candidate_count"] == 1
    assert summary["funds"][0]["excluded_mapping_candidates"] == [
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
    assert summary["funds"][0]["candidate_narrative_count"] == 1
    assert summary["funds"][0]["candidate_narratives"] == [
        {
            "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "name": "Consumer Electronics Globalization",
            "canonical_taxonomy": "Technology Hardware",
            "status": "candidate",
            "source": "mapping_exclusion_review",
            "triggering_stock_codes": ["688036"],
            "related_exclusion_ids": ["EX_SEMI_688036"],
            "human_review_status": "candidate",
            "rationale": "Device exposure candidate, not semiconductor capex.",
        }
    ]
    assert summary["funds"][0]["candidate_review_queue_item_count"] == 1
    assert summary["funds"][0]["candidate_review_queue_items"] == [
        {
            "review_item_id": "RQ_C_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "candidate_narrative_id": "C_CONSUMER_ELECTRONICS_GLOBALIZATION",
            "name": "Consumer Electronics Globalization",
            "status": "candidate",
            "human_review_status": "candidate",
            "available_actions": ["approve", "reject", "defer"],
            "related_exclusion_ids": ["EX_SEMI_688036"],
        }
    ]
    assert (tmp_path / "real_fund_smoke_summary.json").exists()
    assert (tmp_path / "real_fund_smoke_summary.md").exists()

    summary_markdown = (tmp_path / "real_fund_smoke_summary.md").read_text()
    assert "Data Quality" in summary_markdown
    assert "Notice" in summary_markdown
    assert "partial" in summary_markdown
    assert "## Mapping Gaps" in summary_markdown
    assert "002572" in summary_markdown
    assert "索菲亚" in summary_markdown
    assert "## Multi-Mapped Holdings" in summary_markdown
    assert "Narrative One, Narrative Two" in summary_markdown
    assert "## Mapping Precision Flags" in summary_markdown
    assert "broad_industry_fallback" in summary_markdown
    assert "curation_review" in summary_markdown
    assert "## Excluded Mapping Candidates" in summary_markdown
    assert "candidate_narrative_review" in summary_markdown
    assert "## Candidate Narratives For Review" in summary_markdown
    assert "Consumer Electronics Globalization" in summary_markdown


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
    assert summary["funds"][0]["unmapped_holdings"] == [
        {
            "stock_code": "UNKNOWN",
            "stock_name": "Unknown",
            "industry": None,
            "weight": None,
        }
    ]
    assert summary["funds"][0]["mapping_precision_flags"] == []
    assert summary["funds"][0]["excluded_mapping_candidates"] == []
    summary_markdown = (tmp_path / "real_fund_smoke_summary.md").read_text(
        encoding="utf-8"
    )
    assert "| 000000 | UNKNOWN | Unknown | - | - |" in summary_markdown


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
    assert summary["funds"][0]["multi_mapped_holdings"] == []
    assert summary["funds"][0]["mapping_precision_flags"] == []
    assert summary["funds"][0]["excluded_mapping_candidates"] == []
    assert "temporary provider failure" in summary["funds"][0]["error"]
    assert (tmp_path / "real_fund_smoke_summary.json").exists()
    assert (tmp_path / "real_fund_smoke_summary.md").exists()
