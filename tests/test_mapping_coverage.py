import json
from pathlib import Path

from src.modules.fund_analysis.mapping import build_mapping_result

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures"


def test_exact_mappings_are_preferred_and_coverage_is_reported():
    holdings = [
        {"stock_code": "NVDA", "stock_name": "NVIDIA", "weight": 0.12},
        {"stock_code": "UNKNOWN", "stock_name": "Unknown", "weight": 0.08},
    ]
    mappings = [
        {
            "stock_code": "NVDA",
            "narrative_id": "N_AI_INFRA",
            "mapping_weight": 0.9,
            "confidence": 0.86,
            "method": "fixture_rule",
        }
    ]
    registry = {
        "N_AI_INFRA": {
            "name": "AI Infrastructure",
            "aliases": [],
            "related_terms": [],
        }
    }

    result = build_mapping_result(holdings, mappings, registry)

    assert result["mappings"] == mappings
    assert result["coverage"]["covered_holding_count"] == 1
    assert result["coverage"]["total_holding_count"] == 2
    assert result["coverage"]["covered_weight"] == 0.12
    assert result["coverage"]["coverage_ratio"] == 0.6
    assert result["coverage"]["mapping_methods"] == {"fixture_rule": 1}
    assert result["unmapped_holdings"] == [
        {"stock_code": "UNKNOWN", "stock_name": "Unknown", "weight": 0.08}
    ]


def test_registry_term_fallback_maps_unmapped_industry_holdings():
    holdings = [
        {
            "stock_code": "999999",
            "stock_name": "测试白酒",
            "weight": 0.1,
            "industry": "食品饮料",
        }
    ]
    registry = {
        "N_BAIJIU_CONSUMPTION": {
            "name": "Premium Baijiu Consumption",
            "aliases": ["baijiu consumption"],
            "related_terms": ["食品饮料", "白酒"],
        }
    }

    result = build_mapping_result(holdings, [], registry)

    assert result["mappings"] == [
        {
            "stock_code": "999999",
            "narrative_id": "N_BAIJIU_CONSUMPTION",
            "mapping_weight": 0.55,
            "confidence": 0.52,
            "method": "registry_term_rule",
            "matched_terms": ["食品饮料", "白酒"],
        }
    ]
    assert result["coverage"]["coverage_ratio"] == 1
    assert result["coverage"]["mapping_methods"] == {"registry_term_rule": 1}
    assert result["unmapped_holdings"] == []
    assert result["mapping_precision_flags"] == []


def test_multi_match_fallback_lowers_confidence_and_flags_review():
    holdings = [
        {
            "stock_code": "300604",
            "stock_name": "长川科技",
            "weight": 0.0646,
            "industry": "电子",
        }
    ]
    registry = {
        "N_SEMI_CAPEX": {
            "name": "Semiconductor Capex Cycle",
            "aliases": [],
            "related_terms": ["电子", "长川科技"],
        },
        "N_DEFENSE_AEROSPACE": {
            "name": "Defense Aerospace",
            "aliases": [],
            "related_terms": ["长川科技"],
        },
    }

    result = build_mapping_result(holdings, [], registry)

    assert [mapping["narrative_id"] for mapping in result["mappings"]] == [
        "N_SEMI_CAPEX",
        "N_DEFENSE_AEROSPACE",
    ]
    assert {mapping["confidence"] for mapping in result["mappings"]} == {0.42}
    assert all(mapping["needs_review"] is True for mapping in result["mappings"])
    assert all(
        mapping["precision_flag"] == "multi_match_fallback"
        for mapping in result["mappings"]
    )
    assert result["mapping_precision_flags"] == [
        {
            "type": "multi_match_fallback",
            "severity": "review",
            "stock_code": "300604",
            "stock_name": "长川科技",
            "industry": "电子",
            "weight": 0.0646,
            "mapping_method": "registry_term_rule",
            "narrative_ids": ["N_SEMI_CAPEX", "N_DEFENSE_AEROSPACE"],
            "narratives": ["Semiconductor Capex Cycle", "Defense Aerospace"],
            "confidence_before": 0.52,
            "confidence_after": 0.42,
            "recommended_action": "manual_review",
        }
    ]


def test_registry_term_fallback_leaves_unmatched_holdings_unmapped():
    holdings = [
        {
            "stock_code": "111111",
            "stock_name": "No Match Co",
            "weight": 0.1,
            "industry": "Unknown Industry",
        }
    ]
    registry = {
        "N_AI_INFRA": {
            "name": "AI Infrastructure",
            "aliases": ["AI compute infrastructure"],
            "related_terms": ["GPU", "datacenter"],
        }
    }

    result = build_mapping_result(holdings, [], registry)

    assert result["mappings"] == []
    assert result["coverage"]["coverage_ratio"] == 0
    assert result["unmapped_holdings"] == holdings
    assert result["mapping_precision_flags"] == []


def test_registry_terms_cover_latest_real_smoke_mapping_gaps():
    holdings = [
        {
            "stock_code": "002594",
            "stock_name": "比亚迪",
            "industry": "汽车",
            "weight": 0.0283,
        },
        {
            "stock_code": "600066",
            "stock_name": "宇通客车",
            "industry": "汽车",
            "weight": 0.0383,
        },
        {
            "stock_code": "603308",
            "stock_name": "应流股份",
            "industry": "机械设备",
            "weight": 0.0356,
        },
        {
            "stock_code": "002246",
            "stock_name": "北化股份",
            "industry": "基础化工",
            "weight": 0.0355,
        },
        {
            "stock_code": "002572",
            "stock_name": "索菲亚",
            "industry": "轻工制造",
            "weight": 0.0403,
        },
        {
            "stock_code": "603816",
            "stock_name": "顾家家居",
            "industry": "轻工制造",
            "weight": 0.0392,
        },
        {
            "stock_code": "002918",
            "stock_name": "蒙娜丽莎",
            "industry": "轻工制造",
            "weight": 0.0376,
        },
    ]
    registry = _fixture_registry_by_id()

    result = build_mapping_result(holdings, [], registry)

    mappings_by_stock = {
        mapping["stock_code"]: mapping["narrative_id"] for mapping in result["mappings"]
    }

    assert result["coverage"]["coverage_ratio"] == 1
    assert result["unmapped_holdings"] == []
    assert mappings_by_stock == {
        "002594": "N_EV_PRICE_WAR",
        "600066": "N_EV_PRICE_WAR",
        "603308": "N_DEFENSE_AEROSPACE",
        "002246": "N_DEFENSE_AEROSPACE",
        "002572": "N_REAL_ESTATE_STABILIZATION",
        "603816": "N_REAL_ESTATE_STABILIZATION",
        "002918": "N_REAL_ESTATE_STABILIZATION",
    }


def _fixture_registry_by_id() -> dict:
    payload = json.loads(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8")
    )
    return {item["narrative_id"]: item for item in payload["narratives"]}
