from __future__ import annotations

from src.providers.factory import select_data_provider
from src.providers.local_gateway_fund import LocalGatewayFundHoldingProvider


class FakeGatewayProvider:
    provider_name = "local-market-data-gateway"

    def fetch_fund_profile(self, *, fund_code: str):
        return [
            {
                "fund_code": fund_code,
                "fund_name": "招商中证白酒指数",
                "fund_type": "index_fund",
                "currency": "CNY",
                "source": "eastmoney",
                "as_of_date": "2015-05-27",
                "source_url": "http://localhost:8700/api/v1/market-data/funds/profile",
                "retrieved_at": "2026-05-27T00:00:00+00:00",
                "data_quality": "fresh",
            }
        ]

    def fetch_fund_holdings(self, *, fund_code: str, limit: int):
        assert limit == 10
        return [
            {
                "fund_code": fund_code,
                "as_of_date": "2026-03-31",
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "weight": 0.1833,
                "holding_change": 0.0295,
                "industry": "食品饮料",
                "source": "eastmoney",
                "source_url": "http://localhost:8700/api/v1/market-data/funds/holdings",
            },
            {
                "fund_code": fund_code,
                "as_of_date": "2026-03-31",
                "stock_code": "000858",
                "stock_name": "五粮液",
                "weight": 0.1614,
                "holding_change": 0.0149,
                "industry": "食品饮料",
                "source": "eastmoney",
                "source_url": "http://localhost:8700/api/v1/market-data/funds/holdings",
            },
        ]


def test_local_gateway_fund_provider_builds_fund_payload():
    provider = LocalGatewayFundHoldingProvider(gateway_provider=FakeGatewayProvider())

    payload = provider.get_fund_holdings("161725")

    assert payload["as_of_date"] == "2026-03-31"
    assert payload["fund"]["fund_code"] == "161725"
    assert payload["fund"]["fund_name"] == "招商中证白酒指数"
    assert payload["fund"]["provider_metadata"]["as_of_date"] == "2026-03-31"
    assert payload["fund"]["provider_metadata"]["provider_name"] == "local-gateway-fund-holdings"
    assert payload["fund"]["provider_metadata"]["data_quality"] == "fresh"
    assert (
        payload["fund"]["provider_metadata"]["source_url"]
        == "http://localhost:8700/api/v1/market-data/funds/holdings"
    )
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


def test_local_gateway_fund_provider_falls_back_to_mock_without_gateway():
    provider = LocalGatewayFundHoldingProvider(gateway_provider=None)

    payload = provider.get_fund_holdings("000001")

    assert payload["fund"]["provider_metadata"]["data_quality"] == "mock"
    assert provider.degradation_events[-1]["type"] == "provider_fallback"
    assert provider.degradation_events[-1]["requested_provider_mode"] == "gateway"


def test_selects_gateway_provider_mode():
    selection = select_data_provider("gateway")

    assert isinstance(selection.provider, LocalGatewayFundHoldingProvider)
