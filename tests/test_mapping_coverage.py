from src.modules.fund_analysis.mapping import build_mapping_result


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
