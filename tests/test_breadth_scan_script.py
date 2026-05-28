from __future__ import annotations

import json

import pytest
from scripts import run_breadth_scan


class FakeBreadthSource:
    def __init__(self):
        self.daily_called = False
        self.daily_request = None

    def fetch_trade_calendar(self, **kwargs):
        return [
            {"exchange": kwargs.get("exchange", "SSE"), "cal_date": "2026-05-20", "is_open": True},
            {"exchange": kwargs.get("exchange", "SSE"), "cal_date": "2026-05-21", "is_open": False},
            {"exchange": kwargs.get("exchange", "SSE"), "cal_date": "2026-05-22", "is_open": True},
        ]

    def fetch_daily_bars(self, **kwargs):
        self.daily_called = True
        self.daily_request = kwargs
        return [
            {
                "symbol": "600519.SH",
                "trade_date": "2026-05-20",
                "close": 10.0,
                "pre_close": 9.5,
                "volume": 100.0,
            },
            {
                "symbol": "600519.SH",
                "trade_date": "2026-05-22",
                "close": 11.0,
                "pre_close": 10.0,
                "volume": 120.0,
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "2026-05-20",
                "close": 8.0,
                "pre_close": 8.2,
                "volume": 80.0,
            },
            {
                "symbol": "000001.SZ",
                "trade_date": "2026-05-22",
                "close": 7.5,
                "pre_close": 8.0,
                "volume": 70.0,
            },
        ]


def test_run_controlled_breadth_scan_executes_with_fake_source():
    source = FakeBreadthSource()

    report = run_breadth_scan.run_controlled_breadth_scan(
        data_source=source,
        symbols=["600519.SH", "000001.SZ"],
        end_date="2026-05-22",
        lookback_trading_days=2,
    )

    assert report["status"] == "completed"
    assert report["data_fetch_mode"] == "daily_bars"
    assert report["bar_count"] == 4
    assert report["metrics"]["advance_count"] == 1
    assert report["metrics"]["decline_count"] == 1
    assert source.daily_request["include_turnover"] is True


def test_run_controlled_breadth_scan_plan_only_does_not_fetch_daily_bars():
    source = FakeBreadthSource()

    report = run_breadth_scan.run_controlled_breadth_scan(
        data_source=source,
        symbols=["600519.SH"],
        end_date="2026-05-22",
        lookback_trading_days=2,
        plan_only=True,
    )

    assert report["status"] == "planned"
    assert report["data_fetch_mode"] is None
    assert report["bar_count"] == 0
    assert source.daily_called is False


def test_resolve_symbol_inputs_defaults_deduplicates_and_rejects_mixed_metadata(tmp_path):
    symbols_file = tmp_path / "symbols.txt"
    symbols_file.write_text("000001.SZ\n600519.SH,000001.SZ\n", encoding="utf-8")

    assert run_breadth_scan.resolve_symbol_inputs(
        symbols_text=None,
        symbols_file=None,
        use_stock_metadata=False,
    ) == list(run_breadth_scan.DEFAULT_SYMBOLS)
    assert run_breadth_scan.resolve_symbol_inputs(
        symbols_text="600519.SH,300750.SZ",
        symbols_file=symbols_file,
        use_stock_metadata=False,
    ) == ["600519.SH", "300750.SZ", "000001.SZ"]
    assert run_breadth_scan.resolve_symbol_inputs(
        symbols_text=None,
        symbols_file=None,
        use_stock_metadata=True,
    ) is None
    with pytest.raises(ValueError, match="cannot be combined"):
        run_breadth_scan.resolve_symbol_inputs(
            symbols_text="600519.SH",
            symbols_file=None,
            use_stock_metadata=True,
        )


def test_main_writes_breadth_scan_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_breadth_scan,
        "ConsolidatedMarketDataSource",
        lambda: FakeBreadthSource(),
    )

    exit_code = run_breadth_scan.main(
        [
            "--symbols",
            "600519.SH,000001.SZ",
            "--end-date",
            "2026-05-22",
            "--lookback-trading-days",
            "2",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads((tmp_path / "breadth_scan_report.json").read_text())
    assert payload["status"] == "completed"
    assert payload["metrics"]["symbol_count"] == 2
    assert (tmp_path / "breadth_scan_report.md").is_file()
