from __future__ import annotations

import pytest
from src.market_data.providers import local_gateway as local_gateway_module
from src.market_data.providers.local_gateway import LocalGatewayMarketDataProvider


def test_local_gateway_provider_fetches_daily_bars_with_normalized_route():
    calls = []

    def fetcher(method, url, json_body, timeout_seconds):
        calls.append((method, url, json_body, timeout_seconds))
        return 200, {
            "data": {
                "rows": [
                    {
                        "symbol": "600519.SH",
                        "trade_date": "2026-05-22",
                        "close": 1.0,
                        "volume": 100.0,
                    }
                ]
            },
            "meta": {"cache": {"hit": True, "mode": "cache"}},
        }

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        timeout_seconds=3.0,
        fetcher=fetcher,
    )

    rows = provider.fetch_daily_bars(
        symbols=["600519.SH"],
        start_date="2026-05-22",
        end_date="2026-05-22",
    )

    assert rows[0]["symbol"] == "600519.SH"
    assert calls == [
        (
            "POST",
            "http://localhost:8700/api/v1/market-data/tushare/daily",
            {
                "symbols": ["600519.SH"],
                "start_date": "2026-05-22",
                "end_date": "2026-05-22",
                "include_turnover": True,
            },
            3.0,
        )
    ]


def test_local_gateway_provider_from_env_reads_timeout(monkeypatch):
    values = {
        "MARKET_DATA_GATEWAY_URL": "http://localhost:8700",
        "MARKET_DATA_GATEWAY_TIMEOUT_SECONDS": "30",
    }
    monkeypatch.setattr(
        local_gateway_module.local_env,
        "get_config_value",
        lambda name: values.get(name),
    )

    provider = LocalGatewayMarketDataProvider.from_env()

    assert provider is not None
    assert provider.timeout_seconds == 30.0


def test_local_gateway_provider_keeps_stock_sector_membership_meta():
    def fetcher(method, url, json_body, timeout_seconds):
        del method, url, json_body, timeout_seconds
        return 200, {
            "data": {"rows": []},
            "meta": {
                "status": "degraded",
                "warning": {
                    "code": "PROVIDER_UNAVAILABLE",
                    "message": "EastMoney fallback request failed.",
                },
            },
        }

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        fetcher=fetcher,
    )

    rows = provider.fetch_stock_sector_memberships(
        symbols=["600519.SH"],
        trade_date="2026-05-22",
    )

    assert rows == []
    assert provider.last_stock_sector_membership_meta["status"] == "degraded"


def test_local_gateway_provider_fetches_fund_profile_and_holdings():
    calls = []

    def fetcher(method, url, json_body, timeout_seconds):
        calls.append((method, url, json_body, timeout_seconds))
        if "/api/v1/market-data/funds/profile" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "fund_code": "161725",
                            "fund_name": "招商中证白酒指数",
                            "fund_type": "index_fund",
                            "currency": "CNY",
                            "source": "eastmoney",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/funds/holdings" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "fund_code": "161725",
                            "as_of_date": "2026-03-31",
                            "stock_code": "600519",
                            "stock_name": "贵州茅台",
                            "weight": 0.1833,
                            "source": "eastmoney",
                        }
                    ]
                }
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        timeout_seconds=3.0,
        fetcher=fetcher,
    )

    profile = provider.fetch_fund_profile(fund_code="161725")
    holdings = provider.fetch_fund_holdings(fund_code="161725", limit=10)

    assert profile[0]["fund_name"] == "招商中证白酒指数"
    assert holdings[0]["stock_code"] == "600519"
    assert calls == [
        (
            "GET",
            "http://localhost:8700/api/v1/market-data/funds/profile?fund_code=161725",
            None,
            3.0,
        ),
        (
            "GET",
            "http://localhost:8700/api/v1/market-data/funds/holdings?"
            "fund_code=161725&limit=10",
            None,
            3.0,
        ),
    ]


def test_local_gateway_provider_uses_async_job_for_large_daily_bar_requests():
    calls = []

    def fetcher(method, url, json_body, timeout_seconds):
        calls.append((method, url, json_body, timeout_seconds))
        if url.endswith("/api/v1/market-data/jobs/daily-bars"):
            return 202, {"data": {"job_id": "daily-bars-1", "status": "accepted"}}
        if url.endswith("/api/v1/market-data/jobs/daily-bars-1"):
            return 200, {
                "data": {
                    "job_id": "daily-bars-1",
                    "status": "completed",
                    "requested_symbols": 2,
                    "completed_symbols": 2,
                    "failed_symbols": 0,
                    "rows_available": 2,
                    "failures": [],
                }
            }
        if "/api/v1/market-data/jobs/daily-bars-1/rows" in url:
            return 200, {
                "data": {
                    "rows": [
                        {"symbol": "600519.SH", "trade_date": "2026-05-22", "close": 1.0},
                        {"symbol": "000001.SZ", "trade_date": "2026-05-22", "close": 2.0},
                    ]
                },
                "meta": {"pagination": {"offset": 0, "limit": 50000, "returned": 2, "total": 2}},
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        timeout_seconds=3.0,
        fetcher=fetcher,
        async_daily_bars_threshold=2,
        job_poll_interval_seconds=0.0,
        job_max_wait_seconds=1.0,
    )

    rows = provider.fetch_daily_bars(
        symbols=["600519.SH", "000001.SZ"],
        start_date="2026-05-18",
        end_date="2026-05-22",
    )

    assert [row["symbol"] for row in rows] == ["600519.SH", "000001.SZ"]
    assert calls[0] == (
        "POST",
        "http://localhost:8700/api/v1/market-data/jobs/daily-bars",
        {
            "provider": "tushare",
            "symbols": ["600519.SH", "000001.SZ"],
            "start_date": "2026-05-18",
            "end_date": "2026-05-22",
            "include_turnover": True,
            "mode": "read_through_cache",
            "allow_stale": True,
            "force_refresh": False,
            "batch_size": 100,
        },
        3.0,
    )
    assert not any("/api/v1/market-data/tushare/daily" in call[1] for call in calls)


def test_local_gateway_provider_paginates_async_job_rows():
    def fetcher(method, url, json_body, timeout_seconds):
        del method, json_body, timeout_seconds
        if url.endswith("/api/v1/market-data/jobs/daily-bars"):
            return 202, {"data": {"job_id": "daily-bars-1", "status": "completed"}}
        if url.endswith("/api/v1/market-data/jobs/daily-bars-1"):
            return 200, {"data": {"status": "completed", "failures": []}}
        if "offset=0" in url:
            return 200, {
                "data": {"rows": [{"symbol": "600519.SH"}, {"symbol": "000001.SZ"}]},
                "meta": {"pagination": {"offset": 0, "limit": 2, "returned": 2, "total": 3}},
            }
        if "offset=2" in url:
            return 200, {
                "data": {"rows": [{"symbol": "300750.SZ"}]},
                "meta": {"pagination": {"offset": 2, "limit": 2, "returned": 1, "total": 3}},
            }
        raise AssertionError(f"unexpected url: {url}")

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        fetcher=fetcher,
        async_daily_bars_threshold=2,
        job_rows_page_size=2,
        job_poll_interval_seconds=0.0,
        job_max_wait_seconds=1.0,
    )

    rows = provider.fetch_daily_bars(
        symbols=["600519.SH", "000001.SZ"],
        start_date="2026-05-18",
        end_date="2026-05-22",
    )

    assert [row["symbol"] for row in rows] == ["600519.SH", "000001.SZ", "300750.SZ"]


def test_local_gateway_provider_fetches_breadth_window_bars_via_job():
    calls = []

    def fetcher(method, url, json_body, timeout_seconds):
        calls.append((method, url, json_body, timeout_seconds))
        if url.endswith("/api/v1/market-data/jobs/breadth-window"):
            return 202, {"data": {"job_id": "breadth-window-1", "status": "accepted"}}
        if url.endswith("/api/v1/market-data/jobs/breadth-window-1"):
            return 200, {
                "data": {
                    "job_id": "breadth-window-1",
                    "job_type": "breadth-window",
                    "status": "completed",
                    "requested_symbols": 2,
                    "completed_symbols": 2,
                    "failed_symbols": 0,
                    "rows_available": 2,
                    "coverage": {
                        "expected_pairs": 2,
                        "returned_pairs": 2,
                        "missing_pairs": 0,
                        "missing_reasons": [],
                    },
                    "failures": [],
                }
            }
        if "/api/v1/market-data/jobs/breadth-window-1/rows" in url:
            return 200, {
                "data": {
                    "rows": [
                        {"symbol": "600519.SH", "trade_date": "2026-05-22", "close": 1.0},
                        {"symbol": "000001.SZ", "trade_date": "2026-05-22", "close": 2.0},
                    ]
                },
                "meta": {"pagination": {"offset": 0, "limit": 50000, "returned": 2, "total": 2}},
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        timeout_seconds=3.0,
        fetcher=fetcher,
        job_poll_interval_seconds=0.0,
        job_max_wait_seconds=1.0,
    )

    rows = provider.fetch_breadth_window_bars(
        symbols=["600519.SH", "000001.SZ"],
        start_date="2026-05-20",
        end_date="2026-05-22",
        lookback_trading_days=2,
        include_turnover=True,
    )

    assert [row["symbol"] for row in rows] == ["600519.SH", "000001.SZ"]
    assert provider.last_breadth_window_job["job_type"] == "breadth-window"
    assert calls[0] == (
        "POST",
        "http://localhost:8700/api/v1/market-data/jobs/breadth-window",
        {
            "provider": "tushare",
            "symbols": ["600519.SH", "000001.SZ"],
            "end_date": "2026-05-22",
            "lookback_trading_days": 2,
            "include_turnover": True,
            "mode": "read_through_cache",
            "allow_stale": True,
        },
        3.0,
    )


def test_local_gateway_provider_raises_when_async_job_times_out():
    def fetcher(method, url, json_body, timeout_seconds):
        del method, json_body, timeout_seconds
        if url.endswith("/api/v1/market-data/jobs/daily-bars"):
            return 202, {"data": {"job_id": "daily-bars-1", "status": "accepted"}}
        if url.endswith("/api/v1/market-data/jobs/daily-bars-1"):
            return 200, {"data": {"status": "running", "completed_symbols": 1}}
        raise AssertionError(f"unexpected url: {url}")

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        fetcher=fetcher,
        async_daily_bars_threshold=2,
        job_poll_interval_seconds=0.0,
        job_max_wait_seconds=0.0,
    )

    with pytest.raises(RuntimeError, match="did not finish"):
        provider.fetch_daily_bars(
            symbols=["600519.SH", "000001.SZ"],
            start_date="2026-05-18",
            end_date="2026-05-22",
        )


def test_local_gateway_provider_fetches_quotes_and_limit_stats():
    def fetcher(method, url, json_body, timeout_seconds):
        del json_body, timeout_seconds
        if "market-quotes" in url:
            assert method == "GET"
            assert "stock_codes=600519" in url
            return 200, {
                "data": {
                    "rows": [
                        {
                            "stock_code": "600519",
                            "latest_price": 1560.0,
                            "retrieved_at": "2026-05-25T00:00:00+08:00",
                        }
                    ]
                }
            }
        assert method == "GET"
        assert "limit-up-down" in url
        return 200, {
            "data": {
                "rows": [
                    {
                        "trade_date": "2026-05-22",
                        "limit_up_count": 2,
                        "limit_down_count": 1,
                    }
                ]
            }
        }

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        fetcher=fetcher,
    )

    quotes = provider.fetch_latest_stock_quotes(["600519"])
    limits = provider.fetch_limit_up_down_stats(trade_date="2026-05-22")

    assert quotes["provider_name"] == "local-market-data-gateway"
    assert quotes["missing_stock_codes"] == []
    assert limits["limit_down_count"] == 1


def test_local_gateway_provider_fetches_can_do_provider_neutral_routes():
    calls = []

    def fetcher(method, url, json_body, timeout_seconds):
        calls.append((method, url, json_body, timeout_seconds))
        if "/api/v1/market-data/sectors/concepts" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "sector_name": "机器人概念",
                            "pct_change": 2.5,
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/etf/spot" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "symbol": "510300",
                            "name": "沪深300ETF",
                            "pct_change": 1.4,
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/market/limit-up-down" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "limit_up_count": 2,
                            "limit_down_count": 1,
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/news/briefs" in url:
            assert method == "POST"
            assert json_body == {
                "source_provider": "tushare",
                "src": "sina",
                "start_datetime": "2026-05-22 09:00:00",
                "end_datetime": "2026-05-22 15:30:00",
                "limit": 20,
            }
            return 200, {
                "data": {
                    "rows": [
                        {
                            "datetime": "2026-05-22 09:01:00",
                            "title": "市场快讯",
                            "content": "正文",
                            "source": "tushare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/capital/northbound" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "net_buy_amount": 12.3,
                            "source": "eastmoney",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/capital/main-flow" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "symbol": "600519.SH",
                            "main_net_inflow": 123.0,
                            "source": "eastmoney",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/etf/flow" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "symbol": "510300.SH",
                            "net_inflow": 456.0,
                            "source": "eastmoney",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/market/dragon-tiger" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "symbol": "000001.SZ",
                            "reason": "日涨幅偏离值达7%",
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/sectors/constituents" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "sector_name": "机器人概念",
                            "symbol": "300024.SZ",
                            "name": "机器人",
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/etf/basic" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "symbol": "510300",
                            "name": "沪深300ETF",
                            "category": "宽基",
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/index/constituents" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "index_symbol": "000300.SH",
                            "symbol": "600519.SH",
                            "name": "贵州茅台",
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/margin/summary" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "financing_balance": 1800000000000.0,
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/margin/detail" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "trade_date": "2026-05-22",
                            "symbol": "600519.SH",
                            "financing_balance": 123000000.0,
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/fundamentals/earnings-calendar" in url:
            return 200, {
                "data": {
                    "rows": [
                        {
                            "symbol": "600519.SH",
                            "name": "贵州茅台",
                            "ann_date": "2026-05-22",
                            "event_type": "notice",
                            "source": "akshare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/chips/cyq" in url:
            assert json_body == {
                "symbols": ["600519.SH"],
                "trade_date": "2026-05-22",
            }
            return 200, {
                "data": {
                    "rows": [
                        {
                            "symbol": "600519.SH",
                            "trade_date": "2026-05-22",
                            "cost_distribution": [
                                {"price": 1500.0, "percent": 0.32},
                                {"price": 1600.0, "percent": 0.18},
                            ],
                            "source": "tushare",
                        }
                    ]
                }
            }
        if "/api/v1/market-data/stocks/sector-memberships" in url:
            assert method == "POST"
            assert json_body == {
                "symbols": ["600519.SH", "300024.SZ"],
                "trade_date": "2026-05-22",
                "sector_types": ["concept"],
                "limit_per_symbol": 20,
                "sector_universe_limit": 0,
            }
            return 200, {
                "data": {
                    "rows": [
                        {
                            "symbol": "300024.SZ",
                            "name": "机器人",
                            "sector_name": "机器人概念",
                            "sector_type": "concept",
                            "source": "eastmoney",
                        }
                    ]
                }
            }
        raise AssertionError(f"unexpected request: {method} {url}")

    provider = LocalGatewayMarketDataProvider(
        base_url="http://localhost:8700",
        timeout_seconds=3.0,
        fetcher=fetcher,
    )

    sectors = provider.fetch_sector_data(trade_date="2026-05-22", limit=5)
    etfs = provider.fetch_etf_spot(limit=5)
    limits = provider.fetch_limit_up_down_stats(trade_date="2026-05-22")
    news = provider.fetch_news_briefs(
        source_provider="tushare",
        src="sina",
        start_datetime="2026-05-22 09:00:00",
        end_datetime="2026-05-22 15:30:00",
        limit=20,
    )
    northbound = provider.fetch_northbound_capital(trade_date="2026-05-22")
    main_flow = provider.fetch_main_capital_flow(trade_date="2026-05-22", limit=5)
    etf_flow = provider.fetch_etf_flow(trade_date="2026-05-22", limit=5)
    dragon_tiger = provider.fetch_dragon_tiger(trade_date="2026-05-22", limit=5)
    sector_constituents = provider.fetch_sector_constituents(
        sector_name="机器人",
        trade_date="2026-05-22",
        limit=5,
    )
    etf_basic = provider.fetch_etf_basic(market="cn", limit=5)
    index_constituents = provider.fetch_index_constituents(
        index_symbol="000300.SH",
        trade_date="2026-05-22",
        limit=5,
    )
    margin_summary = provider.fetch_margin_summary(trade_date="2026-05-22")
    margin_detail = provider.fetch_margin_detail(trade_date="2026-05-22", limit=5)
    earnings_calendar = provider.fetch_earnings_calendar(
        start_date="2026-05-22",
        end_date="2026-06-05",
        limit=5,
    )
    cyq_chips = provider.fetch_cyq_chips(
        symbols=["600519.SH"],
        trade_date="2026-05-22",
    )
    memberships = provider.fetch_stock_sector_memberships(
        symbols=["600519.SH", "300024.SZ"],
        trade_date="2026-05-22",
        sector_types=["concept"],
        limit_per_symbol=20,
        sector_universe_limit=0,
    )

    assert sectors[0]["sector_name"] == "机器人概念"
    assert etfs[0]["symbol"] == "510300"
    assert limits["limit_up_count"] == 2
    assert news[0]["title"] == "市场快讯"
    assert northbound["net_buy_amount"] == 12.3
    assert main_flow[0]["main_net_inflow"] == 123.0
    assert etf_flow[0]["net_inflow"] == 456.0
    assert dragon_tiger[0]["reason"] == "日涨幅偏离值达7%"
    assert sector_constituents[0]["sector_name"] == "机器人概念"
    assert etf_basic[0]["category"] == "宽基"
    assert index_constituents[0]["index_symbol"] == "000300.SH"
    assert margin_summary["financing_balance"] == 1800000000000.0
    assert margin_detail[0]["symbol"] == "600519.SH"
    assert earnings_calendar[0]["event_type"] == "notice"
    assert cyq_chips[0]["cost_distribution"][0]["price"] == 1500.0
    assert memberships[0]["sector_name"] == "机器人概念"
    assert calls[-1] == (
        "POST",
        "http://localhost:8700/api/v1/market-data/stocks/sector-memberships",
        {
            "symbols": ["600519.SH", "300024.SZ"],
            "sector_types": ["concept"],
            "limit_per_symbol": 20,
            "sector_universe_limit": 0,
            "trade_date": "2026-05-22",
        },
        3.0,
    )
    assert calls[0][1] == (
        "http://localhost:8700/api/v1/market-data/sectors/concepts?"
        "limit=5&trade_date=2026-05-22"
    )
    assert calls[1][1] == "http://localhost:8700/api/v1/market-data/etf/spot?limit=5"
    assert calls[2][1] == (
        "http://localhost:8700/api/v1/market-data/market/limit-up-down?"
        "trade_date=2026-05-22"
    )
