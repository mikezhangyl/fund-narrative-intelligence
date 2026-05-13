import json
from urllib.error import URLError

from src.providers.eastmoney import (
    EastmoneyFundHoldingProvider,
    normalize_eastmoney_holdings_response,
)
from src.providers.factory import select_data_provider


def test_normalizes_eastmoney_fund_holdings_response():
    response = {
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

    payload = normalize_eastmoney_holdings_response(
        response=response,
        fund_code="161725",
        source_url="https://example.test/fund",
        retrieved_at="2026-05-13T00:00:00Z",
    )

    assert payload["as_of_date"] == "2026-03-31"
    assert payload["fund"]["fund_code"] == "161725"
    assert payload["fund"]["provider_metadata"]["provider_name"] == "eastmoney-fundmobapi"
    assert payload["fund"]["provider_metadata"]["data_quality"] == "fresh"
    assert payload["holdings"] == [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "weight": 0.1833,
            "holding_change": 0.0295,
            "industry": "食品饮料",
        },
        {
            "stock_code": "000858",
            "stock_name": "五粮液",
            "weight": 0.1614,
            "holding_change": 0.0149,
            "industry": "食品饮料",
        },
    ]


def test_selects_explicit_eastmoney_provider_mode():
    selection = select_data_provider("eastmoney")

    assert isinstance(selection.provider, EastmoneyFundHoldingProvider)


def test_eastmoney_provider_falls_back_to_mock_on_fetch_error():
    def failing_fetcher(_url: str) -> dict:
        raise URLError("network unavailable")

    provider = EastmoneyFundHoldingProvider(fetcher=failing_fetcher)

    payload = provider.get_fund_holdings("000001")

    assert payload["fund"]["provider_metadata"]["data_quality"] == "mock"
    assert provider.degradation_events
    assert provider.degradation_events[0]["type"] == "provider_fallback"


def test_eastmoney_mode_keeps_pipeline_artifacts_when_fallback_is_needed(tmp_path):
    def failing_fetcher(_url: str) -> dict:
        raise URLError("network unavailable")

    provider = EastmoneyFundHoldingProvider(fetcher=failing_fetcher)
    payload = provider.get_fund_holdings("000001")

    assert json.dumps(payload, ensure_ascii=False)
