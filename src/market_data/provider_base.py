from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from src.market_data.cache import FileSystemMarketDataCache, MarketDataCache
from src.market_data.request_logging import (
    JsonlProviderRequestLogger,
    ProviderRequestLogEntry,
    ProviderRequestLogger,
    utc_now_iso,
)


class MarketDataProvider(Protocol):
    provider_name: str

    def fetch_daily_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        include_turnover: bool = False,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_sector_data(self, *, trade_date: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_etf_data(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class ProviderConfig:
    pacing_seconds: float = 0.2
    retry_attempts: int = 2
    retry_backoff_seconds: float = 0.5
    cache_max_age_seconds: int | None = None


class ProviderRuntime:
    def __init__(
        self,
        *,
        provider_name: str,
        cache: MarketDataCache | None = None,
        logger: ProviderRequestLogger | None = None,
        pacing_seconds: float = 0.2,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.5,
        cache_max_age_seconds: int | None = None,
    ):
        self.provider_name = provider_name
        self.cache = cache or FileSystemMarketDataCache()
        self.logger = logger or JsonlProviderRequestLogger()
        self.config = ProviderConfig(
            pacing_seconds=pacing_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            cache_max_age_seconds=cache_max_age_seconds,
        )
        self._last_request_at = 0.0

    def cached_request(
        self,
        *,
        endpoint: str,
        key_parts: dict[str, Any],
        loader: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        cached = self.cache.get(
            namespace=f"{self.provider_name}.{endpoint}",
            key_parts=key_parts,
            max_age_seconds=self.config.cache_max_age_seconds,
        )
        if cached is not None:
            self.logger.log(
                ProviderRequestLogEntry(
                    provider=self.provider_name,
                    endpoint=endpoint,
                    request_time=utc_now_iso(),
                    response_time_ms=0.0,
                    status="cache_hit",
                    retry_count=0,
                    row_count=_row_count(cached),
                    cache_hit=True,
                )
            )
            return list(cached)
        rows = self.request(endpoint=endpoint, loader=loader)
        self.cache.set(
            namespace=f"{self.provider_name}.{endpoint}",
            key_parts=key_parts,
            payload=rows,
        )
        return rows

    def request(
        self,
        *,
        endpoint: str,
        loader: Callable[[], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        request_time = utc_now_iso()
        started = time.perf_counter()
        last_error: Exception | None = None
        attempts = max(1, self.config.retry_attempts + 1)
        for attempt in range(attempts):
            self._pace()
            try:
                rows = loader()
                self.logger.log(
                    ProviderRequestLogEntry(
                        provider=self.provider_name,
                        endpoint=endpoint,
                        request_time=request_time,
                        response_time_ms=_elapsed_ms(started),
                        status="success",
                        retry_count=attempt,
                        row_count=len(rows),
                    )
                )
                return rows
            except Exception as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(self.config.retry_backoff_seconds * (attempt + 1))
        failure_reason = str(last_error or "unknown failure")
        self.logger.log(
            ProviderRequestLogEntry(
                provider=self.provider_name,
                endpoint=endpoint,
                request_time=request_time,
                response_time_ms=_elapsed_ms(started),
                status="failure",
                retry_count=attempts - 1,
                failure_reason=failure_reason,
            )
        )
        raise RuntimeError(f"{self.provider_name}.{endpoint} failed: {failure_reason}")

    def _pace(self) -> None:
        if self.config.pacing_seconds <= 0:
            return
        elapsed = time.perf_counter() - self._last_request_at
        sleep_for = self.config.pacing_seconds - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last_request_at = time.perf_counter()


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _row_count(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    return None
