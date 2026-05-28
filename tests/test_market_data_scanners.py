from __future__ import annotations

from datetime import date, timedelta

from src.market_data.capabilities import load_data_capability_registry
from src.scanners.breadth_scanner import (
    BreadthScanner,
    BreadthScanPlanner,
    execute_breadth_scan,
)
from src.scanners.sector_scanner import SectorScanner, execute_sector_scan


def test_breadth_scanner_calculates_deterministic_metrics():
    bars = []
    first_day = date(2025, 1, 1)
    for day in range(1, 366):
        trade_date = (first_day + timedelta(days=day - 1)).isoformat()
        bars.append(
            {
                "symbol": "AAA",
                "trade_date": trade_date,
                "close": float(day),
                "pre_close": float(day - 1),
                "volume": float(day),
            }
        )
        bars.append(
            {
                "symbol": "BBB",
                "trade_date": trade_date,
                "close": float(400 - day),
                "pre_close": float(401 - day),
                "volume": float(400 - day),
            }
        )

    metrics = BreadthScanner().calculate(bars)

    assert metrics["trade_date"] == "2025-12-31"
    assert metrics["ma20_breadth"] == 50.0
    assert metrics["advance_count"] == 1
    assert metrics["decline_count"] == 1
    assert metrics["new_high_count"] == 1
    assert metrics["new_low_count"] == 1
    assert metrics["volume_expansion"] is False


def test_breadth_scan_planner_uses_registry_and_trade_calendar():
    class Source:
        def __init__(self):
            self.calendar_request = None

        def fetch_trade_calendar(self, **kwargs):
            self.calendar_request = kwargs
            return [
                {
                    "exchange": "SSE",
                    "cal_date": "2026-05-20",
                    "is_open": True,
                },
                {
                    "exchange": "SSE",
                    "cal_date": "2026-05-21",
                    "is_open": False,
                },
                {
                    "exchange": "SSE",
                    "cal_date": "2026-05-22",
                    "is_open": True,
                },
                {
                    "exchange": "SSE",
                    "cal_date": "2026-05-25",
                    "is_open": True,
                },
            ]

    source = Source()
    plan = BreadthScanPlanner(
        registry=load_data_capability_registry()
    ).build_plan(
        data_source=source,
        symbols=["600519.SH", "000001.SZ"],
        end_date="2026-05-25",
        lookback_trading_days=3,
    )

    assert plan.can_run is True
    assert plan.required_datasets == (
        "a_share_daily_bars",
        "stock_metadata",
        "trade_calendar",
    )
    assert plan.missing_datasets == ()
    assert plan.trade_dates == ("2026-05-20", "2026-05-22", "2026-05-25")
    assert plan.start_date == "2026-05-20"
    assert plan.end_date == "2026-05-25"
    assert source.calendar_request["exchange"] == "SSE"
    assert source.calendar_request["end_date"] == "2026-05-25"


def test_breadth_scan_planner_can_resolve_symbols_from_stock_metadata():
    class Source:
        def fetch_stock_metadata(self):
            return [
                {"ts_code": "600519.SH", "name": "贵州茅台"},
                {"ts_code": "000001.SZ", "name": "平安银行"},
                {"ts_code": "", "name": "bad"},
            ]

        def fetch_trade_calendar(self, **kwargs):
            return [
                {"exchange": "SSE", "cal_date": "20260522", "is_open": 1},
                {"exchange": "SSE", "cal_date": "20260525", "is_open": 1},
            ]

    plan = BreadthScanPlanner(
        registry=load_data_capability_registry()
    ).build_plan(
        data_source=Source(),
        end_date="20260525",
        lookback_trading_days=2,
    )

    assert plan.symbols == ("600519.SH", "000001.SZ")
    assert plan.trade_dates == ("2026-05-22", "2026-05-25")
    assert plan.can_run is True


def test_execute_breadth_scan_fetches_daily_bars_from_plan():
    class Source:
        def __init__(self):
            self.daily_request = None

        def fetch_daily_bars(self, **kwargs):
            self.daily_request = kwargs
            return [
                {
                    "symbol": "AAA",
                    "trade_date": "2026-05-20",
                    "close": 1.0,
                    "pre_close": 0.9,
                    "volume": 10.0,
                },
                {
                    "symbol": "AAA",
                    "trade_date": "2026-05-22",
                    "close": 1.2,
                    "pre_close": 1.0,
                    "volume": 12.0,
                },
                {
                    "symbol": "BBB",
                    "trade_date": "2026-05-20",
                    "close": 2.0,
                    "pre_close": 2.1,
                    "volume": 20.0,
                },
                {
                    "symbol": "BBB",
                    "trade_date": "2026-05-22",
                    "close": 1.8,
                    "pre_close": 2.0,
                    "volume": 18.0,
                },
            ]

    plan = BreadthScanPlanner(
        registry=load_data_capability_registry()
    ).build_static_plan(
        symbols=["AAA", "BBB"],
        trade_dates=["2026-05-20", "2026-05-22"],
        analysis_capability="advance_decline",
    )

    result = execute_breadth_scan(data_source=Source(), plan=plan)

    assert result["scan_plan"]["analysis_capability"] == "advance_decline"
    assert result["scan_plan"]["start_date"] == "2026-05-20"
    assert result["metrics"]["advance_count"] == 1
    assert result["metrics"]["decline_count"] == 1


def test_execute_breadth_scan_prefers_breadth_window_when_available():
    class Source:
        def __init__(self):
            self.breadth_request = None
            self.daily_called = False

        def fetch_breadth_window_bars(self, **kwargs):
            self.breadth_request = kwargs
            return [
                {
                    "symbol": "AAA",
                    "trade_date": "2026-05-20",
                    "close": 1.0,
                    "pre_close": 0.9,
                    "volume": 10.0,
                },
                {
                    "symbol": "AAA",
                    "trade_date": "2026-05-22",
                    "close": 1.2,
                    "pre_close": 1.0,
                    "volume": 12.0,
                },
            ]

        def fetch_daily_bars(self, **kwargs):
            self.daily_called = True
            return []

    source = Source()
    plan = BreadthScanPlanner(
        registry=load_data_capability_registry()
    ).build_static_plan(
        symbols=["AAA"],
        trade_dates=["2026-05-20", "2026-05-22"],
    )

    result = execute_breadth_scan(data_source=source, plan=plan)

    assert result["data_fetch_mode"] == "breadth_window"
    assert result["bar_count"] == 2
    assert source.daily_called is False
    assert source.breadth_request == {
        "symbols": ["AAA"],
        "start_date": "2026-05-20",
        "end_date": "2026-05-22",
        "lookback_trading_days": 2,
        "include_turnover": True,
    }


def test_sector_scanner_ranks_sectors_and_etfs():
    result = SectorScanner().rank(
        sectors=[
            {"sector_name": "低空经济", "pct_change": 1.2, "amount": 10.0},
            {"sector_name": "机器人", "pct_change": 3.5, "amount": 8.0},
        ],
        etfs=[
            {"symbol": "510300", "pct_change": 0.4, "amount": 100.0},
            {"symbol": "159915", "pct_change": 1.1, "amount": 80.0},
        ],
    )

    assert result["top_sectors"][0]["sector_name"] == "机器人"
    assert result["top_etfs"][0]["symbol"] == "159915"


def test_execute_sector_scan_returns_partial_when_sector_endpoint_fails():
    class Source:
        def fetch_sector_data(self, trade_date):
            raise RuntimeError("sector endpoint blocked")

        def fetch_etf_data(self, symbols, start_date, end_date):
            return [
                {
                    "symbol": symbols[0],
                    "trade_date": end_date,
                    "pct_change": 1.0,
                    "amount": 10.0,
                }
            ]

    result = execute_sector_scan(
        data_source=Source(),
        trade_date="2026-05-22",
        etf_symbols=["510300.SH"],
    )

    assert result.status == "partial"
    assert result.sector_count == 0
    assert result.etf_count == 1
    assert result.failures[0]["capability"] == "sector_concepts"
    assert "sector endpoint blocked" in result.failures[0]["reason"]


def test_execute_sector_scan_returns_partial_when_sector_endpoint_is_empty():
    class Source:
        def fetch_sector_data(self, trade_date):
            return []

        def fetch_etf_data(self, symbols, start_date, end_date):
            return [
                {
                    "symbol": symbols[0],
                    "trade_date": end_date,
                    "pct_change": 1.0,
                    "amount": 10.0,
                }
            ]

    result = execute_sector_scan(
        data_source=Source(),
        trade_date="2026-05-22",
        etf_symbols=["510300.SH"],
    )

    assert result.status == "partial"
    assert result.sector_count == 0
    assert result.etf_count == 1
    assert result.failures[0]["capability"] == "sector_concepts"
    assert "returned no rows" in result.failures[0]["reason"]
