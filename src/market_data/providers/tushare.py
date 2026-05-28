from __future__ import annotations

import hashlib
from time import perf_counter
from typing import Any

from src.market_data.cache import MarketDataCache
from src.market_data.provider_base import ProviderRuntime
from src.market_data.request_logging import ProviderRequestLogger, utc_now_iso
from src.market_data.schemas import DailyBar, ProviderHealth
from src.providers.tushare_common import (
    TushareFetcher,
    as_float,
    iso_date,
    query_tushare_rows,
)
from src.providers.tushare_market import (
    TushareMarketDataProvider as ExistingTushareMarketQuoteProvider,
)

TUSHARE_PROVIDER_NAME = "tushare"

_DAILY_FIELDS = "ts_code,trade_date,open,high,low,close,pre_close,vol,amount"
_DAILY_BASIC_FIELDS = "ts_code,trade_date,turnover_rate,volume_ratio,total_mv,circ_mv"
_STOCK_BASIC_FIELDS = "ts_code,symbol,name,area,industry,list_date"
_TRADE_CAL_FIELDS = "exchange,cal_date,is_open,pretrade_date"


class TushareMarketDataProvider:
    provider_name = TUSHARE_PROVIDER_NAME

    def __init__(
        self,
        *,
        token: str | None = None,
        fetcher: TushareFetcher | None = None,
        cache: MarketDataCache | None = None,
        logger: ProviderRequestLogger | None = None,
        pacing_seconds: float = 0.2,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.5,
        cache_max_age_seconds: int | None = None,
        quote_provider: ExistingTushareMarketQuoteProvider | None = None,
    ):
        self.quote_provider = (
            quote_provider
            or ExistingTushareMarketQuoteProvider(token=token, fetcher=fetcher)
        )
        self.token = self.quote_provider.token
        self.fetcher = fetcher
        self.runtime = ProviderRuntime(
            provider_name=self.provider_name,
            cache=cache,
            logger=logger,
            pacing_seconds=pacing_seconds,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
            cache_max_age_seconds=cache_max_age_seconds,
        )

    def fetch_latest_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        return self.quote_provider.get_stock_quotes(stock_codes)

    def fetch_daily_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        include_turnover: bool = False,
    ) -> list[dict[str, Any]]:
        self._require_token()
        daily_rows = self._query(
            endpoint="daily",
            params={
                "ts_code": ",".join(symbols),
                "start_date": _compact_date(start_date),
                "end_date": _compact_date(end_date),
            },
            fields=_DAILY_FIELDS,
        )
        turnover_by_key: dict[tuple[str, str], float | None] = {}
        if include_turnover:
            turnover_rows = self._query(
                endpoint="daily_basic",
                params={
                    "ts_code": ",".join(symbols),
                    "start_date": _compact_date(start_date),
                    "end_date": _compact_date(end_date),
                },
                fields=_DAILY_BASIC_FIELDS,
            )
            turnover_by_key = {
                (str(row.get("ts_code")), iso_date(row.get("trade_date"))): as_float(
                    row.get("turnover_rate")
                )
                for row in turnover_rows
            }
        return [
            _daily_bar_from_tushare_row(
                row=row,
                turnover_rate=turnover_by_key.get(
                    (str(row.get("ts_code")), iso_date(row.get("trade_date")))
                ),
                source=self.provider_name,
            )
            for row in daily_rows
        ]

    def fetch_index_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        self._require_token()
        rows = self._query(
            endpoint="index_daily",
            params={
                "ts_code": ",".join(symbols),
                "start_date": _compact_date(start_date),
                "end_date": _compact_date(end_date),
            },
            fields=_DAILY_FIELDS,
        )
        return [
            _daily_bar_from_tushare_row(
                row=row,
                turnover_rate=None,
                source=self.provider_name,
            )
            for row in rows
        ]

    def fetch_etf_data(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        self._require_token()
        rows = self._query(
            endpoint="fund_daily",
            params={
                "ts_code": ",".join(symbols),
                "start_date": _compact_date(start_date),
                "end_date": _compact_date(end_date),
            },
            fields=_DAILY_FIELDS,
        )
        return [
            _daily_bar_from_tushare_row(
                row=row,
                turnover_rate=None,
                source=self.provider_name,
            )
            for row in rows
        ]

    def fetch_stock_metadata(self) -> list[dict[str, Any]]:
        self._require_token()
        return self._query(
            endpoint="stock_basic",
            params={"exchange": "", "list_status": "L"},
            fields=_STOCK_BASIC_FIELDS,
        )

    def fetch_trade_calendar(
        self,
        *,
        exchange: str = "SSE",
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        self._require_token()
        rows = self._query(
            endpoint="trade_cal",
            params={
                "exchange": exchange,
                "start_date": _compact_date(start_date),
                "end_date": _compact_date(end_date),
            },
            fields=_TRADE_CAL_FIELDS,
        )
        return [_trade_calendar_row(row, source=self.provider_name) for row in rows]

    def fetch_sector_data(self, *, trade_date: str | None = None) -> list[dict[str, Any]]:
        return []

    def health_check(self) -> dict[str, Any]:
        started = perf_counter()
        endpoint = "stock_basic"
        try:
            rows = self.fetch_stock_metadata()
            sample = rows[:1]
            return ProviderHealth(
                provider=self.provider_name,
                endpoint=endpoint,
                ok=True,
                latency_ms=round((perf_counter() - started) * 1000, 3),
                checked_at=utc_now_iso(),
                row_count=len(rows),
                schema_fingerprint=_schema_fingerprint(sample),
            ).to_dict()
        except Exception as exc:
            return ProviderHealth(
                provider=self.provider_name,
                endpoint=endpoint,
                ok=False,
                latency_ms=round((perf_counter() - started) * 1000, 3),
                checked_at=utc_now_iso(),
                error=str(exc),
            ).to_dict()

    def _query(
        self,
        *,
        endpoint: str,
        params: dict[str, Any],
        fields: str,
    ) -> list[dict[str, Any]]:
        return self.runtime.cached_request(
            endpoint=endpoint,
            key_parts={"params": params, "fields": fields},
            loader=lambda: query_tushare_rows(
                token=str(self.token),
                api_name=endpoint,
                params=params,
                fields=fields,
                fetcher=self.fetcher,
            ),
        )

    def _require_token(self) -> None:
        if not self.token:
            raise RuntimeError("TUSHARE_TOKEN is not configured")


def _daily_bar_from_tushare_row(
    *,
    row: dict[str, Any],
    turnover_rate: float | None,
    source: str,
) -> dict[str, Any]:
    return DailyBar(
        symbol=str(row.get("ts_code") or ""),
        trade_date=iso_date(row.get("trade_date")),
        open=as_float(row.get("open")),
        high=as_float(row.get("high")),
        low=as_float(row.get("low")),
        close=as_float(row.get("close")),
        pre_close=as_float(row.get("pre_close")),
        volume=as_float(row.get("vol")),
        amount=as_float(row.get("amount")),
        turnover_rate=turnover_rate,
        source=source,
    ).to_dict()


def _trade_calendar_row(row: dict[str, Any], *, source: str) -> dict[str, Any]:
    return {
        "exchange": str(row.get("exchange") or ""),
        "cal_date": iso_date(row.get("cal_date")),
        "is_open": _as_bool(row.get("is_open")),
        "pretrade_date": iso_date(row.get("pretrade_date")),
        "source": source,
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip() in {"1", "true", "True", "Y", "y"}


def _compact_date(value: str) -> str:
    return value.replace("-", "")


def _schema_fingerprint(rows: list[dict[str, Any]]) -> str:
    keys = sorted({key for row in rows for key in row})
    return hashlib.sha256(",".join(keys).encode("utf-8")).hexdigest()
