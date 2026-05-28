from __future__ import annotations

import pytest
from src.market_data.providers.local_gateway import GatewayJobTerminalError
from src.market_data.source_layer import (
    ConsolidatedMarketDataSource,
    LiveValidationPlan,
)


class QuoteProvider:
    provider_name = "eastmoney-market-quote"

    def get_stock_quotes(self, stock_codes):
        return {
            "provider_name": self.provider_name,
            "quotes": [
                {
                    "stock_code": stock_codes[0],
                    "latest_price": 1560.0,
                    "retrieved_at": "2026-05-24T10:00:00+00:00",
                }
            ],
            "missing_stock_codes": [],
        }


class TushareProvider:
    provider_name = "tushare"

    def fetch_latest_stock_quotes(self, stock_codes):
        return {"provider_name": "tushare-market-quote", "quotes": []}

    def fetch_stock_metadata(self):
        return [{"ts_code": "600519.SH", "name": "贵州茅台"}]

    def fetch_daily_bars(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][0],
                "trade_date": kwargs["end_date"],
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 100.0,
                "source": self.provider_name,
            }
        ]

    def fetch_index_bars(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][0],
                "trade_date": kwargs["end_date"],
                "close": 3005.0,
                "source": self.provider_name,
            }
        ]

    def fetch_etf_data(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][0],
                "trade_date": kwargs["end_date"],
                "close": 4.05,
                "source": self.provider_name,
            }
        ]

    def fetch_trade_calendar(self, **kwargs):
        return [
            {
                "exchange": kwargs["exchange"],
                "cal_date": kwargs["end_date"],
                "is_open": True,
                "source": self.provider_name,
            }
        ]

    def health_check(self):
        return {"provider": self.provider_name, "ok": True}


class AkshareProvider:
    provider_name = "akshare"

    def fetch_daily_bars(self, **kwargs):
        return [{"symbol": kwargs["symbols"][0], "source": self.provider_name}]

    def fetch_etf_data(self, **kwargs):
        return [{"symbol": kwargs["symbols"][0], "source": self.provider_name}]

    def fetch_sector_data(self, **kwargs):
        return [
            {
                "sector_name": "机器人概念",
                "pct_change": 2.5,
                "amount": 123.0,
                "source": self.provider_name,
            }
        ]

    def fetch_limit_up_down_stats(self, **kwargs):
        return {
            "trade_date": kwargs["trade_date"],
            "limit_up_count": 2,
            "limit_down_count": 1,
            "source": self.provider_name,
        }

    def health_check(self):
        return {"provider": self.provider_name, "ok": True}


class GatewayProvider:
    provider_name = "local-market-data-gateway"

    def fetch_latest_stock_quotes(self, stock_codes):
        return {
            "provider_name": self.provider_name,
            "quotes": [
                {
                    "stock_code": stock_codes[0],
                    "latest_price": 1600.0,
                    "retrieved_at": "2026-05-24T10:00:00+00:00",
                }
            ],
            "missing_stock_codes": [],
        }

    def fetch_stock_metadata(self):
        return [{"ts_code": "600519.SH", "source": self.provider_name}]

    def fetch_daily_bars(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][0],
                "trade_date": kwargs["end_date"],
                "close": 1.0,
                "volume": 100.0,
                "source": self.provider_name,
            }
        ]

    def fetch_breadth_window_bars(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][0],
                "trade_date": kwargs["end_date"],
                "close": 1.0,
                "volume": 100.0,
                "source": self.provider_name,
                "job_type": "breadth-window",
            }
        ]

    def fetch_etf_spot(self, **kwargs):
        return [
            {
                "symbol": "510300",
                "name": "沪深300ETF",
                "pct_change": 1.4,
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_sector_data(self, **kwargs):
        return [
            {
                "sector_name": "机器人概念",
                "pct_change": 2.5,
                "amount": 123.0,
                "source": self.provider_name,
            }
        ]

    def fetch_limit_up_down_stats(self, **kwargs):
        return {
            "trade_date": kwargs["trade_date"],
            "limit_up_count": 2,
            "limit_down_count": 1,
            "source": self.provider_name,
        }

    def fetch_news_briefs(self, **kwargs):
        return [
            {
                "datetime": kwargs["start_datetime"],
                "title": "市场快讯",
                "content": "正文",
                "source": self.provider_name,
            }
        ]

    def fetch_northbound_capital(self, **kwargs):
        return {
            "trade_date": kwargs["trade_date"],
            "net_buy_amount": 12.3,
            "source": self.provider_name,
        }

    def fetch_main_capital_flow(self, **kwargs):
        return [
            {
                "trade_date": kwargs["trade_date"],
                "symbol": "600519.SH",
                "main_net_inflow": 123.0,
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_etf_flow(self, **kwargs):
        return [
            {
                "trade_date": kwargs["trade_date"],
                "symbol": "510300.SH",
                "net_inflow": 456.0,
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_dragon_tiger(self, **kwargs):
        return [
            {
                "trade_date": kwargs["trade_date"],
                "symbol": "000001.SZ",
                "reason": "日涨幅偏离值达7%",
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_sector_constituents(self, **kwargs):
        return [
            {
                "sector_name": kwargs["sector_name"],
                "symbol": "300024.SZ",
                "name": "机器人",
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_etf_basic(self, **kwargs):
        return [
            {
                "symbol": "510300",
                "name": "沪深300ETF",
                "category": kwargs["market"],
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_index_constituents(self, **kwargs):
        return [
            {
                "index_symbol": kwargs["index_symbol"],
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_margin_summary(self, **kwargs):
        return {
            "trade_date": kwargs["trade_date"],
            "financing_balance": 1800000000000.0,
            "source": self.provider_name,
        }

    def fetch_margin_detail(self, **kwargs):
        return [
            {
                "trade_date": kwargs["trade_date"],
                "symbol": "600519.SH",
                "financing_balance": 123000000.0,
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_earnings_calendar(self, **kwargs):
        return [
            {
                "symbol": "600519.SH",
                "name": "贵州茅台",
                "ann_date": kwargs["start_date"],
                "event_type": "notice",
                "source": self.provider_name,
            }
        ][: kwargs["limit"]]

    def fetch_cyq_chips(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][0],
                "trade_date": kwargs["trade_date"],
                "cost_distribution": [{"price": 1500.0, "percent": 0.32}],
                "source": self.provider_name,
            }
        ]

    def fetch_stock_sector_memberships(self, **kwargs):
        return [
            {
                "symbol": kwargs["symbols"][-1],
                "sector_name": "机器人概念",
                "sector_type": kwargs["sector_types"][0],
                "sector_universe_limit": kwargs["sector_universe_limit"],
                "source": self.provider_name,
            }
        ][: kwargs["limit_per_symbol"]]


def test_consolidated_source_routes_capabilities_to_existing_layers():
    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
    )

    quotes = source.fetch_latest_stock_quotes(["600519"])
    metadata = source.fetch_stock_metadata()
    daily = source.fetch_daily_bars(
        symbols=["600519.SH"],
        start_date="20260522",
        end_date="20260522",
    )
    sectors = source.fetch_sector_data(trade_date="20260522")
    limits = source.fetch_limit_up_down_stats(trade_date="20260522")
    calendar = source.fetch_trade_calendar(
        exchange="SSE",
        start_date="20260522",
        end_date="20260522",
    )

    assert quotes["provider_name"] == "eastmoney-market-quote"
    assert metadata[0]["ts_code"] == "600519.SH"
    assert daily[0]["source"] == "tushare"
    assert calendar[0]["cal_date"] == "20260522"
    assert sectors[0]["source"] == "akshare"
    assert limits["limit_up_count"] == 2


def test_consolidated_source_falls_back_for_daily_bars():
    class FailingTushare(TushareProvider):
        def fetch_daily_bars(self, **kwargs):
            raise RuntimeError("tushare throttled")

    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=FailingTushare(),
        akshare_provider=AkshareProvider(),
    )

    rows = source.fetch_daily_bars(
        symbols=["600519"],
        start_date="20260522",
        end_date="20260522",
    )

    assert rows[0]["source"] == "akshare"
    assert source.degradation_events[-1]["primary_provider"] == "tushare"
    assert source.degradation_events[-1]["fallback_provider"] == "akshare"


def test_live_validation_returns_consolidated_matrix_without_throwing():
    class FailingQuoteProvider(QuoteProvider):
        def get_stock_quotes(self, stock_codes):
            raise RuntimeError("quote blocked")

    source = ConsolidatedMarketDataSource(
        quote_provider=FailingQuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
    )

    report = source.run_live_validation(
        LiveValidationPlan(
            stock_codes=["600519"],
            tushare_symbols=["600519.SH"],
            index_symbols=["000001.SH"],
            etf_symbols=["510300"],
            trade_date="20260522",
        )
    )

    checks = {item["capability"]: item for item in report["checks"]}
    assert report["summary"]["total_checks"] == 7
    assert checks["latest_stock_quotes"]["availability"] is False
    assert checks["daily_bars"]["availability"] is True
    assert checks["trade_calendar"]["availability"] is True
    assert checks["sector_data"]["availability"] is True
    assert "quote blocked" in checks["latest_stock_quotes"]["failure_reason"]


def test_consolidated_source_prefers_gateway_when_configured():
    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=GatewayProvider(),
    )

    quotes = source.fetch_latest_stock_quotes(["600519"])
    metadata = source.fetch_stock_metadata()
    rows = source.fetch_daily_bars(
        symbols=["600519.SH"],
        start_date="20260522",
        end_date="20260522",
    )

    assert quotes["provider_name"] == "local-market-data-gateway"
    assert metadata[0]["source"] == "local-market-data-gateway"
    assert rows[0]["source"] == "local-market-data-gateway"


def test_consolidated_source_exposes_gateway_can_do_methods():
    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=GatewayProvider(),
    )

    sectors = source.fetch_sector_data(trade_date="2026-05-22", limit=5)
    etfs = source.fetch_etf_spot(limit=5)
    limits = source.fetch_limit_up_down_stats(trade_date="2026-05-22")
    news = source.fetch_news_briefs(
        source_provider="tushare",
        src="sina",
        start_datetime="2026-05-22 09:00:00",
        end_datetime="2026-05-22 15:30:00",
        limit=20,
    )
    northbound = source.fetch_northbound_capital(trade_date="2026-05-22")
    main_flow = source.fetch_main_capital_flow(trade_date="2026-05-22", limit=5)
    etf_flow = source.fetch_etf_flow(trade_date="2026-05-22", limit=5)
    dragon_tiger = source.fetch_dragon_tiger(trade_date="2026-05-22", limit=5)
    sector_constituents = source.fetch_sector_constituents(
        sector_name="机器人",
        trade_date="2026-05-22",
        limit=5,
    )
    etf_basic = source.fetch_etf_basic(market="cn", limit=5)
    index_constituents = source.fetch_index_constituents(
        index_symbol="000300.SH",
        trade_date="2026-05-22",
        limit=5,
    )
    margin_summary = source.fetch_margin_summary(trade_date="2026-05-22")
    margin_detail = source.fetch_margin_detail(trade_date="2026-05-22", limit=5)
    earnings_calendar = source.fetch_earnings_calendar(
        start_date="2026-05-22",
        end_date="2026-06-05",
        limit=5,
    )
    cyq_chips = source.fetch_cyq_chips(
        symbols=["600519.SH"],
        trade_date="2026-05-22",
    )
    memberships = source.fetch_stock_sector_memberships(
        symbols=["600519.SH", "300024.SZ"],
        trade_date="2026-05-22",
        sector_types=["concept"],
        limit_per_symbol=20,
        sector_universe_limit=0,
    )

    assert sectors[0]["source"] == "local-market-data-gateway"
    assert etfs[0]["symbol"] == "510300"
    assert limits["source"] == "local-market-data-gateway"
    assert news[0]["title"] == "市场快讯"
    assert northbound["net_buy_amount"] == 12.3
    assert main_flow[0]["symbol"] == "600519.SH"
    assert etf_flow[0]["symbol"] == "510300.SH"
    assert dragon_tiger[0]["reason"] == "日涨幅偏离值达7%"
    assert sector_constituents[0]["name"] == "机器人"
    assert etf_basic[0]["category"] == "cn"
    assert memberships[0]["sector_universe_limit"] == 0
    assert index_constituents[0]["index_symbol"] == "000300.SH"
    assert margin_summary["financing_balance"] == 1800000000000.0
    assert margin_detail[0]["symbol"] == "600519.SH"
    assert earnings_calendar[0]["event_type"] == "notice"
    assert cyq_chips[0]["cost_distribution"][0]["percent"] == 0.32
    assert memberships[0]["sector_name"] == "机器人概念"


def test_consolidated_source_records_gateway_degraded_membership_meta():
    class DegradedGateway(GatewayProvider):
        provider_name = "local-market-data-gateway"

        def __init__(self):
            self.last_stock_sector_membership_meta = None

        def fetch_stock_sector_memberships(self, **kwargs):
            del kwargs
            self.last_stock_sector_membership_meta = {
                "status": "degraded",
                "warning": {
                    "code": "PROVIDER_UNAVAILABLE",
                    "message": "EastMoney fallback request failed.",
                },
            }
            return []

    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=DegradedGateway(),
    )

    rows = source.fetch_stock_sector_memberships(
        symbols=["600519.SH"],
        trade_date="2026-05-22",
        sector_types=["concept"],
        limit_per_symbol=20,
        sector_universe_limit=0,
    )

    assert rows == []
    assert source.degradation_events[-1] == {
        "type": "provider_degraded",
        "capability": "stock_sector_membership",
        "primary_provider": "local-market-data-gateway",
        "fallback_provider": "",
        "reason": "PROVIDER_UNAVAILABLE: EastMoney fallback request failed.",
    }


def test_consolidated_source_uses_gateway_breadth_window_when_configured():
    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=GatewayProvider(),
    )

    rows = source.fetch_breadth_window_bars(
        symbols=["600519.SH"],
        start_date="2026-05-20",
        end_date="2026-05-22",
        lookback_trading_days=2,
    )

    assert rows[0]["source"] == "local-market-data-gateway"
    assert rows[0]["job_type"] == "breadth-window"


def test_consolidated_source_falls_back_from_breadth_window_to_daily_bars():
    class FailingGateway(GatewayProvider):
        def fetch_breadth_window_bars(self, **kwargs):
            raise RuntimeError("breadth job unavailable")

    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=FailingGateway(),
    )

    rows = source.fetch_breadth_window_bars(
        symbols=["600519.SH"],
        start_date="2026-05-20",
        end_date="2026-05-22",
        lookback_trading_days=2,
    )

    assert rows[0]["source"] == "local-market-data-gateway"
    assert source.degradation_events[-1]["capability"] == "breadth_window_bars"


def test_consolidated_source_does_not_fallback_from_terminal_breadth_window_job():
    class CancelledGateway(GatewayProvider):
        def fetch_breadth_window_bars(self, **kwargs):
            raise GatewayJobTerminalError("gateway breadth-window job ended with cancelled")

    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=CancelledGateway(),
    )

    with pytest.raises(GatewayJobTerminalError, match="cancelled"):
        source.fetch_breadth_window_bars(
            symbols=["600519.SH"],
            start_date="2026-05-20",
            end_date="2026-05-22",
            lookback_trading_days=2,
        )

    assert source.degradation_events[-1]["type"] == "provider_terminal_failure"


def test_consolidated_source_falls_back_when_gateway_fails():
    class FailingGateway(GatewayProvider):
        def fetch_daily_bars(self, **kwargs):
            raise RuntimeError("gateway unavailable")

    source = ConsolidatedMarketDataSource(
        quote_provider=QuoteProvider(),
        tushare_provider=TushareProvider(),
        akshare_provider=AkshareProvider(),
        gateway_provider=FailingGateway(),
    )

    rows = source.fetch_daily_bars(
        symbols=["600519.SH"],
        start_date="20260522",
        end_date="20260522",
    )

    assert rows[0]["source"] == "tushare"
    assert source.degradation_events[-1]["primary_provider"] == "local-market-data-gateway"
