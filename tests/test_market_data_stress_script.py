from __future__ import annotations

import json

from scripts import run_market_data_stress


class FakeStressProvider:
    def fetch_stock_metadata(self):
        return [
            {"ts_code": "600519.SH"},
            {"ts_code": "000001.SZ"},
            {"ts_code": "300750.SZ"},
        ]

    def fetch_daily_bars(self, symbols, start_date, end_date, include_turnover=False):
        return [
            {
                "symbol": symbol,
                "trade_date": end_date,
                "close": 1.0,
                "pre_close": 0.9,
                "volume": 100.0,
                "turnover_rate": 1.0 if include_turnover else None,
            }
            for symbol in symbols
        ]

    def fetch_sector_data(self, trade_date):
        return [{"sector_name": "机器人", "pct_change": 1.0, "amount": 100.0}]

    def fetch_etf_data(self, symbols, start_date, end_date):
        return [
            {"symbol": symbol, "trade_date": end_date, "pct_change": 1.0, "amount": 10.0}
            for symbol in symbols
        ]


class FailingSectorProvider(FakeStressProvider):
    def fetch_sector_data(self, trade_date):
        raise RuntimeError("sector endpoint blocked")


def test_run_stress_suite_covers_historical_daily_and_sector_modes():
    report = run_market_data_stress.run_stress_suite(
        provider=FakeStressProvider(),
        symbols=["600519.SH", "000001.SZ", "600519.SH"],
        etf_symbols=["510300.SH"],
        start_date="2026-05-18",
        end_date="2026-05-22",
        trade_date="2026-05-22",
        modes=("historical", "daily", "sector"),
        batch_size=2,
    )

    assert report["status"] == "completed"
    assert report["summary"]["test_count"] == 3
    assert report["summary"]["request_volume"] == 5
    assert report["summary"]["rows_returned"] == 7
    assert report["results"]["historical"]["duplicate_symbols"] == 1
    assert report["results"]["daily"]["duplicate_symbols"] == 1


def test_run_stress_suite_preserves_failure_reasons():
    report = run_market_data_stress.run_stress_suite(
        provider=FailingSectorProvider(),
        symbols=["600519.SH"],
        etf_symbols=["510300.SH"],
        start_date="2026-05-18",
        end_date="2026-05-22",
        trade_date="2026-05-22",
        modes=("sector",),
        batch_size=2,
    )

    assert report["status"] == "completed_with_failures"
    assert report["results"]["sector"]["failure_reasons"] == (
        "sector_data: sector endpoint blocked",
    )
    assert "sector endpoint blocked" in run_market_data_stress._markdown_report(report)


def test_resolve_stress_symbols_uses_explicit_or_metadata_inputs():
    provider = FakeStressProvider()

    assert run_market_data_stress.resolve_stress_symbols(
        data_source=provider,
        symbol_input=["A", "B", "C"],
        max_symbols=2,
    ) == ["A", "B"]
    assert run_market_data_stress.resolve_stress_symbols(
        data_source=provider,
        symbol_input=None,
        max_symbols=2,
    ) == ["600519.SH", "000001.SZ"]


def test_market_data_stress_cli_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        run_market_data_stress,
        "ConsolidatedMarketDataSource",
        lambda: FakeStressProvider(),
    )

    exit_code = run_market_data_stress.main(
        [
            "--mode",
            "daily",
            "--symbols",
            "600519.SH,000001.SZ",
            "--trade-date",
            "2026-05-22",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads((tmp_path / "stress_report.json").read_text())
    assert payload["status"] == "completed"
    assert payload["summary"]["test_count"] == 1
    assert (tmp_path / "stress_report.md").is_file()
