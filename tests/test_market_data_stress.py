from __future__ import annotations

from src.market_data.stress import MarketDataStressTester


class Provider:
    def fetch_daily_bars(self, symbols, start_date, end_date, include_turnover=False):
        return [
            {
                "symbol": symbol,
                "trade_date": end_date,
                "close": 1.0,
                "pre_close": 0.9,
                "volume": 100.0,
                "source": "fake",
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


def test_stress_tester_reports_request_volume_failures_and_memory():
    tester = MarketDataStressTester(provider=Provider(), batch_size=2)

    historical = tester.run_historical_scan(
        symbols=["A", "B", "C"],
        start_date="20240101",
        end_date="20260522",
    )
    daily = tester.run_incremental_daily_update(
        symbols=["A", "B", "C"],
        trade_date="20260522",
    )
    sector = tester.run_sector_rotation_scan(
        etf_symbols=["510300"],
        trade_date="20260522",
    )

    assert historical.request_volume == 2
    assert historical.rows_returned == 3
    assert historical.failure_count == 0
    assert historical.peak_memory_kb >= 0
    assert daily.duplicate_symbols == 0
    assert sector.rows_returned == 2


def test_stress_tester_records_failure_reasons():
    class FailingSectorProvider(Provider):
        def fetch_sector_data(self, trade_date):
            raise RuntimeError("sector endpoint blocked")

    tester = MarketDataStressTester(provider=FailingSectorProvider(), batch_size=2)

    result = tester.run_sector_rotation_scan(
        etf_symbols=["510300"],
        trade_date="20260522",
    )

    assert result.failure_count == 1
    assert result.failure_reasons == ("sector_data: sector endpoint blocked",)


def test_stress_tester_records_empty_sector_data_as_completeness_failure():
    class EmptySectorProvider(Provider):
        def fetch_sector_data(self, trade_date):
            return []

    tester = MarketDataStressTester(provider=EmptySectorProvider(), batch_size=2)

    result = tester.run_sector_rotation_scan(
        etf_symbols=["510300"],
        trade_date="20260522",
    )

    assert result.failure_count == 1
    assert result.rows_returned == 1
    assert result.failure_reasons == ("sector_data: returned no rows",)
