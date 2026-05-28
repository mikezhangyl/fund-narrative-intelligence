import json

import pytest
from src.orchestrator import run_pipeline
from src.providers.local_gateway_fund import LocalGatewayFundHoldingProvider
from src.providers.routing import ProviderRouter, ProviderRoutingConfig


def test_provider_routing_config_rejects_unknown_layer():
    with pytest.raises(ValueError) as exc:
        ProviderRoutingConfig.from_dict(
            {
                "unsupported_layer": {
                    "primary": "foo",
                }
            }
        )

    assert "Unsupported provider routing layer" in str(exc.value)


def test_provider_router_resolves_builtin_tushare_and_akshare_placeholders():
    router = ProviderRouter(
        provider_routing={
            "holdings": {"primary": "tushare", "fallback": "eastmoney"},
            "financial_metrics": {"primary": "tushare", "fallback": "eastmoney"},
            "valuation_snapshots": {"primary": "tushare", "fallback": "eastmoney"},
            "market_quotes": {"primary": "tushare", "fallback": "eastmoney"},
        }
    )

    holdings = router.resolve("holdings", default_primary="eastmoney")
    financial = router.resolve("financial_metrics", default_primary="eastmoney")
    valuation = router.resolve("valuation_snapshots", default_primary="eastmoney")
    quotes = router.resolve("market_quotes", default_primary="eastmoney")

    assert holdings.primary_provider.provider_name == "tushare-fund-portfolio"
    assert holdings.fallback_provider.provider_name == "eastmoney-fundmobapi"
    assert financial.primary_provider.provider_name == "tushare-financial-metrics"
    assert financial.fallback_provider.provider_name == "eastmoney-financial-metrics"
    assert valuation.primary_provider.provider_name == "tushare-valuation"
    assert valuation.fallback_provider.provider_name == "eastmoney-valuation"
    assert quotes.primary_provider.provider_name == "tushare-market-quote"
    assert quotes.fallback_provider.provider_name == "eastmoney-market-quote"


def test_provider_router_resolves_gateway_holdings_provider():
    router = ProviderRouter(
        provider_routing={
            "holdings": {"primary": "gateway", "fallback": "eastmoney"},
        }
    )

    holdings = router.resolve("holdings", default_primary="mock")

    assert isinstance(holdings.primary_provider, LocalGatewayFundHoldingProvider)
    assert holdings.fallback_provider.provider_name == "eastmoney-fundmobapi"


def test_provider_routing_uses_primary_financial_metrics_provider(tmp_path):
    class FakeTushareFinancialMetricsProvider:
        provider_name = "tushare-financial-metrics"
        provider_version = "tushare-financial-metrics-v1"
        source_url = "https://api.tushare.pro"
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
                        "report_type": "Q1",
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
        provider_routing={
            "financial_metrics": {
                "primary": "tushare",
                "fallback": "eastmoney",
            }
        },
        provider_factory_overrides={
            "financial_metrics": {
                "tushare": lambda: FakeTushareFinancialMetricsProvider(),
            }
        },
    )

    raw = json.loads(artifacts["raw"].read_text())
    layer = raw["provider_foundation"]["layers"]["financial_metrics"]

    assert raw["financial_metrics"]["provider_name"] == "tushare-financial-metrics"
    assert layer["provider_name"] == "tushare-financial-metrics"
    assert not any(
        event["type"] == "provider_fallback"
        and event.get("layer") == "financial_metrics"
        for event in raw["degradation_events"]
    )


def test_provider_routing_falls_back_for_unavailable_financial_metrics(tmp_path):
    class FakeEastmoneyFinancialMetricsProvider:
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
        provider_routing={
            "financial_metrics": {
                "primary": "tushare",
                "fallback": "eastmoney",
            }
        },
        provider_factory_overrides={
            "financial_metrics": {
                "eastmoney": lambda: FakeEastmoneyFinancialMetricsProvider(),
            }
        },
    )

    raw = json.loads(artifacts["raw"].read_text())

    assert raw["financial_metrics"]["provider_name"] == "eastmoney-financial-metrics"
    assert any(
        event["type"] == "provider_fallback"
        and event.get("layer") == "financial_metrics"
        and event.get("provider") == "tushare"
        and event.get("fallback_provider") == "eastmoney"
        for event in raw["degradation_events"]
    )


def test_provider_routing_falls_back_for_valuation_snapshots(tmp_path):
    class FakeEastmoneyValuationProvider:
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
        provider_routing={
            "valuation_snapshots": {
                "primary": "tushare",
                "fallback": "eastmoney",
            }
        },
        provider_factory_overrides={
            "valuation_snapshots": {
                "eastmoney": lambda: FakeEastmoneyValuationProvider(),
            }
        },
    )

    raw = json.loads(artifacts["raw"].read_text())
    layer = raw["provider_foundation"]["layers"]["valuation"]

    assert raw["valuation_snapshots"]["provider_name"] == "eastmoney-valuation"
    assert layer["provider_name"] == "eastmoney-valuation"
    assert any(
        event["type"] == "provider_fallback"
        and event.get("layer") == "valuation_snapshots"
        and event.get("provider") == "tushare"
        and event.get("fallback_provider") == "eastmoney"
        for event in raw["degradation_events"]
    )


def test_provider_routing_falls_back_for_market_quotes(tmp_path):
    class FakeEastmoneyMarketQuoteProvider:
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
                        "source_provider": "eastmoney",
                        "source_url": self.source_url,
                        "latest_price": 1000.0,
                        "change_percent": 1.5,
                        "change_amount": 14.7,
                        "volume": 123456.0,
                        "amount": 123456789.0,
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
        provider_routing={
            "market_quotes": {
                "primary": "akshare",
                "fallback": "eastmoney",
            }
        },
        provider_factory_overrides={
            "market_quotes": {
                "eastmoney": lambda: FakeEastmoneyMarketQuoteProvider(),
            }
        },
    )

    raw = json.loads(artifacts["raw"].read_text())
    layer = raw["provider_foundation"]["layers"]["market_quotes"]

    assert raw["market_quotes"]["provider_name"] == "eastmoney-market-quote"
    assert layer["provider_name"] == "eastmoney-market-quote"
    assert any(
        event["type"] == "provider_fallback"
        and event.get("layer") == "market_quotes"
        and event.get("provider") == "akshare"
        and event.get("fallback_provider") == "eastmoney"
        for event in raw["degradation_events"]
    )
