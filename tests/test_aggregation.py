from src.modules.fund_analysis.aggregation import aggregate_fund_narratives


def test_aggregates_stock_mappings_into_ranked_fund_narratives():
    holdings = [
        {"stock_code": "NVDA", "weight": 0.12},
        {"stock_code": "VST", "weight": 0.08},
        {"stock_code": "MSFT", "weight": 0.10},
    ]
    mappings = [
        {
            "stock_code": "NVDA",
            "narrative_id": "N_AI_INFRA",
            "mapping_weight": 0.9,
            "confidence": 0.86,
        },
        {
            "stock_code": "VST",
            "narrative_id": "N_AI_POWER",
            "mapping_weight": 0.9,
            "confidence": 0.84,
        },
        {
            "stock_code": "VST",
            "narrative_id": "N_AI_INFRA",
            "mapping_weight": 0.6,
            "confidence": 0.78,
        },
        {
            "stock_code": "MSFT",
            "narrative_id": "N_AI_APPS",
            "mapping_weight": 0.7,
            "confidence": 0.75,
        },
    ]
    registry = {
        "N_AI_INFRA": {"name": "AI Infrastructure", "level": 2},
        "N_AI_POWER": {"name": "AI Power Demand", "level": 3},
        "N_AI_APPS": {"name": "AI Applications", "level": 2},
    }

    exposures = aggregate_fund_narratives(holdings, mappings, registry)

    assert [item["narrative_id"] for item in exposures] == [
        "N_AI_INFRA",
        "N_AI_POWER",
        "N_AI_APPS",
    ]
    assert exposures[0]["name"] == "AI Infrastructure"
    assert exposures[0]["raw_exposure"] == 0.156
    assert round(sum(item["normalized_exposure"] for item in exposures), 6) == 1
    assert 0 < exposures[0]["confidence"] <= 1
