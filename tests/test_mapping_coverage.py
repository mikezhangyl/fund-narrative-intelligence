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
    assert result["mapping_rationales"] == [
        {
            "stock_code": "NVDA",
            "stock_name": "NVIDIA",
            "industry": None,
            "narrative_id": "N_AI_INFRA",
            "narrative_name": "AI Infrastructure",
            "method": "fixture_rule",
            "confidence": 0.86,
            "mapping_weight": 0.9,
            "matched_terms": [],
            "needs_review": False,
            "precision_flag": None,
            "reason": (
                "Explicit fixture_rule mapping from the stock-narrative "
                "mapping fixture."
            ),
        }
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
    assert result["mapping_rationales"] == [
        {
            "stock_code": "999999",
            "stock_name": "测试白酒",
            "industry": "食品饮料",
            "narrative_id": "N_BAIJIU_CONSUMPTION",
            "narrative_name": "Premium Baijiu Consumption",
            "method": "registry_term_rule",
            "confidence": 0.52,
            "mapping_weight": 0.55,
            "matched_terms": ["食品饮料", "白酒"],
            "needs_review": False,
            "precision_flag": None,
            "reason": (
                "Matched registry terms against stock code/name/industry: "
                "食品饮料, 白酒."
            ),
        }
    ]


def test_broad_industry_only_fallback_is_flagged_for_curation_review():
    holdings = [
        {
            "stock_code": "123456",
            "stock_name": "测试科技",
            "weight": 0.1,
            "industry": "电子",
        }
    ]
    registry = {
        "N_SEMI_CAPEX": {
            "name": "Semiconductor Capex Cycle",
            "aliases": [],
            "related_terms": ["电子"],
        }
    }

    result = build_mapping_result(holdings, [], registry)

    assert result["mappings"] == [
        {
            "stock_code": "123456",
            "narrative_id": "N_SEMI_CAPEX",
            "mapping_weight": 0.55,
            "confidence": 0.48,
            "method": "registry_term_rule",
            "matched_terms": ["电子"],
            "needs_review": True,
            "precision_flag": "broad_industry_fallback",
        }
    ]
    assert result["mapping_precision_flags"] == [
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
    assert result["mapping_rationales"] == [
        {
            "stock_code": "123456",
            "stock_name": "测试科技",
            "industry": "电子",
            "narrative_id": "N_SEMI_CAPEX",
            "narrative_name": "Semiconductor Capex Cycle",
            "method": "registry_term_rule",
            "confidence": 0.48,
            "mapping_weight": 0.55,
            "matched_terms": ["电子"],
            "needs_review": True,
            "precision_flag": "broad_industry_fallback",
            "reason": (
                "Matched broad industry-only registry terms against holding "
                "industry: 电子."
            ),
        }
    ]


def test_excluded_fallback_candidate_is_not_mapped_or_scored():
    holdings = [
        {
            "stock_code": "688036",
            "stock_name": "传音控股",
            "weight": 0.06,
            "industry": "电子",
        }
    ]
    registry = {
        "N_SEMI_CAPEX": {
            "name": "Semiconductor Capex Cycle",
            "aliases": [],
            "related_terms": ["电子"],
        }
    }
    exclusions = [
        {
            "exclusion_id": "EX_SEMI_688036",
            "stock_code": "688036",
            "narrative_id": "N_SEMI_CAPEX",
            "method": "registry_term_rule",
            "reason": (
                "Consumer electronics device exposure is too broad for "
                "Semiconductor Capex."
            ),
        }
    ]

    result = build_mapping_result(holdings, [], registry, exclusions=exclusions)

    assert result["mappings"] == []
    assert result["coverage"]["coverage_ratio"] == 0
    assert result["unmapped_holdings"] == holdings
    assert result["mapping_precision_flags"] == []
    assert result["mapping_rationales"] == []
    assert result["excluded_mapping_candidates"] == [
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
    assert result["mapping_rationales"] == [
        {
            "stock_code": "300604",
            "stock_name": "长川科技",
            "industry": "电子",
            "narrative_id": "N_SEMI_CAPEX",
            "narrative_name": "Semiconductor Capex Cycle",
            "method": "registry_term_rule",
            "confidence": 0.42,
            "mapping_weight": 0.55,
            "matched_terms": ["电子", "长川科技"],
            "needs_review": True,
            "precision_flag": "multi_match_fallback",
            "reason": (
                "Matched registry terms against stock code/name/industry: "
                "电子, 长川科技."
            ),
        },
        {
            "stock_code": "300604",
            "stock_name": "长川科技",
            "industry": "电子",
            "narrative_id": "N_DEFENSE_AEROSPACE",
            "narrative_name": "Defense Aerospace",
            "method": "registry_term_rule",
            "confidence": 0.42,
            "mapping_weight": 0.55,
            "matched_terms": ["长川科技"],
            "needs_review": True,
            "precision_flag": "multi_match_fallback",
            "reason": (
                "Matched registry terms against stock code/name/industry: "
                "长川科技."
            ),
        },
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
    assert result["mapping_rationales"] == []


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


def test_registry_specific_terms_reduce_clear_real_smoke_broad_flags():
    holdings = [
        {
            "stock_code": "603737",
            "stock_name": "三棵树",
            "industry": "建筑材料",
            "weight": 0.0301,
        },
        {
            "stock_code": "600383",
            "stock_name": "金地集团",
            "industry": "房地产",
            "weight": 0.0294,
        },
        {
            "stock_code": "688563",
            "stock_name": "航材股份",
            "industry": "国防军工",
            "weight": 0.0401,
        },
        {
            "stock_code": "688239",
            "stock_name": "航宇科技",
            "industry": "国防军工",
            "weight": 0.0388,
        },
        {
            "stock_code": "600760",
            "stock_name": "中航沈飞",
            "industry": "国防军工",
            "weight": 0.0342,
        },
        {
            "stock_code": "002653",
            "stock_name": "海思科",
            "industry": "医药生物",
            "weight": 0.041,
        },
        {
            "stock_code": "688506",
            "stock_name": "百利天恒",
            "industry": "医药生物",
            "weight": 0.039,
        },
        {
            "stock_code": "002422",
            "stock_name": "科伦药业",
            "industry": "医药生物",
            "weight": 0.038,
        },
        {
            "stock_code": "002294",
            "stock_name": "信立泰",
            "industry": "医药生物",
            "weight": 0.037,
        },
        {
            "stock_code": "300347",
            "stock_name": "泰格医药",
            "industry": "医药生物",
            "weight": 0.036,
        },
        {
            "stock_code": "688578",
            "stock_name": "艾力斯",
            "industry": "医药生物",
            "weight": 0.035,
        },
        {
            "stock_code": "603659",
            "stock_name": "璞泰来",
            "industry": "电力设备",
            "weight": 0.044,
        },
        {
            "stock_code": "002202",
            "stock_name": "金风科技",
            "industry": "电力设备",
            "weight": 0.043,
        },
        {
            "stock_code": "603806",
            "stock_name": "福斯特",
            "industry": "电力设备",
            "weight": 0.042,
        },
        {
            "stock_code": "002487",
            "stock_name": "大金重工",
            "industry": "电力设备",
            "weight": 0.041,
        },
        {
            "stock_code": "603198",
            "stock_name": "迎驾贡酒",
            "industry": "食品饮料",
            "weight": 0.035,
        },
        {
            "stock_code": "600702",
            "stock_name": "舍得酒业",
            "industry": "食品饮料",
            "weight": 0.034,
        },
        {
            "stock_code": "300661",
            "stock_name": "圣邦股份",
            "industry": "电子",
            "weight": 0.038,
        },
        {
            "stock_code": "301269",
            "stock_name": "华大九天",
            "industry": "计算机",
            "weight": 0.037,
        },
        {
            "stock_code": "688361",
            "stock_name": "中科飞测",
            "industry": "电子",
            "weight": 0.036,
        },
        {
            "stock_code": "688072",
            "stock_name": "拓荆科技",
            "industry": "电子",
            "weight": 0.035,
        },
    ]
    registry = _fixture_registry_by_id()

    result = build_mapping_result(holdings, [], registry)

    assert result["coverage"]["coverage_ratio"] == 1
    assert result["mapping_precision_flags"] == []
    assert {
        mapping["stock_code"]: mapping["narrative_id"]
        for mapping in result["mappings"]
    } == {
        "603737": "N_REAL_ESTATE_STABILIZATION",
        "600383": "N_REAL_ESTATE_STABILIZATION",
        "688563": "N_DEFENSE_AEROSPACE",
        "688239": "N_DEFENSE_AEROSPACE",
        "600760": "N_DEFENSE_AEROSPACE",
        "002653": "N_HEALTHCARE_INNOVATION",
        "688506": "N_HEALTHCARE_INNOVATION",
        "002422": "N_HEALTHCARE_INNOVATION",
        "002294": "N_HEALTHCARE_INNOVATION",
        "300347": "N_HEALTHCARE_INNOVATION",
        "688578": "N_HEALTHCARE_INNOVATION",
        "603659": "N_NEW_ENERGY_EQUIPMENT",
        "002202": "N_NEW_ENERGY_EQUIPMENT",
        "603806": "N_NEW_ENERGY_EQUIPMENT",
        "002487": "N_NEW_ENERGY_EQUIPMENT",
        "603198": "N_BAIJIU_CONSUMPTION",
        "600702": "N_BAIJIU_CONSUMPTION",
        "300661": "N_SEMI_CAPEX",
        "301269": "N_SEMI_CAPEX",
        "688361": "N_SEMI_CAPEX",
        "688072": "N_SEMI_CAPEX",
    }


def _fixture_registry_by_id() -> dict:
    payload = json.loads(
        (FIXTURE_DIR / "narrative_registry.json").read_text(encoding="utf-8")
    )
    return {item["narrative_id"]: item for item in payload["narratives"]}
