from __future__ import annotations

import platform
import resource
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class StressTestResult:
    test_name: str
    total_runtime_seconds: float
    request_volume: int
    rows_returned: int
    failure_count: int
    throttling_events: int
    peak_memory_kb: int
    duplicate_symbols: int = 0
    failure_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MarketDataStressTester:
    def __init__(self, *, provider: Any, batch_size: int = 500):
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.provider = provider
        self.batch_size = batch_size

    def run_historical_scan(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> StressTestResult:
        started = perf_counter()
        rows_returned = 0
        failures = 0
        failure_reasons: list[str] = []
        requests = 0
        for batch in _batches(symbols, self.batch_size):
            requests += 1
            try:
                rows = self.provider.fetch_daily_bars(
                    symbols=batch,
                    start_date=start_date,
                    end_date=end_date,
                    include_turnover=True,
                )
                rows_returned += len(rows)
            except Exception as exc:
                failures += 1
                failure_reasons.append(str(exc))
        return _result(
            test_name="historical_scan",
            started=started,
            request_volume=requests,
            rows_returned=rows_returned,
            failure_count=failures,
            duplicate_symbols=_duplicate_count(symbols),
            failure_reasons=tuple(failure_reasons),
        )

    def run_incremental_daily_update(
        self,
        *,
        symbols: list[str],
        trade_date: str,
    ) -> StressTestResult:
        started = perf_counter()
        rows_returned = 0
        failures = 0
        failure_reasons: list[str] = []
        requests = 0
        unique_symbols = list(dict.fromkeys(symbols))
        for batch in _batches(unique_symbols, self.batch_size):
            requests += 1
            try:
                rows = self.provider.fetch_daily_bars(
                    symbols=batch,
                    start_date=trade_date,
                    end_date=trade_date,
                    include_turnover=True,
                )
                rows_returned += len(rows)
            except Exception as exc:
                failures += 1
                failure_reasons.append(str(exc))
        return _result(
            test_name="incremental_daily_update",
            started=started,
            request_volume=requests,
            rows_returned=rows_returned,
            failure_count=failures,
            duplicate_symbols=_duplicate_count(symbols),
            failure_reasons=tuple(failure_reasons),
        )

    def run_sector_rotation_scan(
        self,
        *,
        etf_symbols: list[str],
        trade_date: str,
    ) -> StressTestResult:
        started = perf_counter()
        failures = 0
        failure_reasons: list[str] = []
        rows_returned = 0
        requests = 0
        try:
            requests += 1
            sector_rows = self.provider.fetch_sector_data(trade_date=trade_date)
            if not sector_rows:
                failures += 1
                failure_reasons.append("sector_data: returned no rows")
            rows_returned += len(sector_rows)
        except Exception as exc:
            failures += 1
            failure_reasons.append(f"sector_data: {exc}")
        try:
            requests += 1
            rows_returned += len(
                self.provider.fetch_etf_data(
                    symbols=etf_symbols,
                    start_date=trade_date,
                    end_date=trade_date,
                )
            )
        except Exception as exc:
            failures += 1
            failure_reasons.append(f"etf_data: {exc}")
        return _result(
            test_name="sector_rotation_scan",
            started=started,
            request_volume=requests,
            rows_returned=rows_returned,
            failure_count=failures,
            duplicate_symbols=_duplicate_count(etf_symbols),
            failure_reasons=tuple(failure_reasons),
        )


def _batches(symbols: list[str], batch_size: int) -> list[list[str]]:
    return [symbols[index : index + batch_size] for index in range(0, len(symbols), batch_size)]


def _duplicate_count(symbols: list[str]) -> int:
    return len(symbols) - len(set(symbols))


def _result(
    *,
    test_name: str,
    started: float,
    request_volume: int,
    rows_returned: int,
    failure_count: int,
    duplicate_symbols: int,
    failure_reasons: tuple[str, ...],
) -> StressTestResult:
    return StressTestResult(
        test_name=test_name,
        total_runtime_seconds=round(perf_counter() - started, 6),
        request_volume=request_volume,
        rows_returned=rows_returned,
        failure_count=failure_count,
        throttling_events=0,
        peak_memory_kb=_peak_memory_kb(),
        duplicate_symbols=duplicate_symbols,
        failure_reasons=failure_reasons,
    )


def _peak_memory_kb() -> int:
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if platform.system() == "Darwin":
        return peak // 1024
    return peak
