from __future__ import annotations

import hashlib
from time import perf_counter
from typing import Any, Callable

from src.market_data.cache import MarketDataCache
from src.market_data.provider_base import ProviderRuntime
from src.market_data.request_logging import ProviderRequestLogger, utc_now_iso
from src.market_data.schemas import DailyBar, ProviderHealth, SectorSnapshot
from src.providers.akshare_market import (
    AkshareMarketDataProvider as ExistingAkshareMarketQuoteProvider,
)
from src.providers.tushare_common import as_float, iso_date

AKSHARE_PROVIDER_NAME = "akshare"
AkshareClientLoader = Callable[[], Any]


class AkShareMarketDataProvider:
    provider_name = AKSHARE_PROVIDER_NAME

    def __init__(
        self,
        *,
        client: Any | None = None,
        client_loader: AkshareClientLoader | None = None,
        cache: MarketDataCache | None = None,
        logger: ProviderRequestLogger | None = None,
        pacing_seconds: float = 0.2,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.5,
        cache_max_age_seconds: int | None = None,
        quote_provider: ExistingAkshareMarketQuoteProvider | None = None,
    ):
        self.quote_provider = (
            quote_provider
            or ExistingAkshareMarketQuoteProvider(
                client=client,
                client_loader=client_loader,
            )
        )
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
        client = self._client()
        rows: list[dict[str, Any]] = []
        for symbol in symbols:
            rows.extend(
                self.runtime.cached_request(
                    endpoint="stock_zh_a_hist",
                    key_parts={
                        "symbol": symbol,
                        "start_date": _compact_date(start_date),
                        "end_date": _compact_date(end_date),
                    },
                    loader=lambda symbol=symbol: _frame_records(
                        client.stock_zh_a_hist(
                            symbol=symbol,
                            period="daily",
                            start_date=_compact_date(start_date),
                            end_date=_compact_date(end_date),
                            adjust="",
                        )
                    ),
                )
            )
        return [_daily_bar_from_akshare_row(row=row, symbol_hint=None) for row in rows]

    def fetch_sector_data(self, *, trade_date: str | None = None) -> list[dict[str, Any]]:
        client = self._client()
        rows = self.runtime.cached_request(
            endpoint="stock_board_concept_name_em",
            key_parts={"trade_date": trade_date or "latest"},
            loader=lambda: _frame_records(client.stock_board_concept_name_em()),
        )
        return [_sector_from_akshare_row(row=row, trade_date=trade_date) for row in rows]

    def fetch_etf_data(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        client = self._client()
        bars: list[dict[str, Any]] = []
        for symbol in symbols:
            rows = self.runtime.cached_request(
                endpoint="fund_etf_hist_em",
                key_parts={
                    "symbol": symbol,
                    "start_date": _compact_date(start_date),
                    "end_date": _compact_date(end_date),
                },
                loader=lambda symbol=symbol: _frame_records(
                    client.fund_etf_hist_em(
                        symbol=symbol,
                        period="daily",
                        start_date=_compact_date(start_date),
                        end_date=_compact_date(end_date),
                        adjust="",
                    )
                ),
            )
            bars.extend(_daily_bar_from_akshare_row(row=row, symbol_hint=symbol) for row in rows)
        return bars

    def fetch_limit_up_down_stats(self, *, trade_date: str) -> dict[str, Any]:
        client = self._client()
        compact_trade_date = _compact_date(trade_date)
        limit_up_rows = self.runtime.cached_request(
            endpoint="stock_zt_pool_em",
            key_parts={"date": compact_trade_date},
            loader=lambda: _frame_records(client.stock_zt_pool_em(date=compact_trade_date)),
        )
        limit_down_rows = self.runtime.cached_request(
            endpoint="stock_zt_pool_dtgc_em",
            key_parts={"date": compact_trade_date},
            loader=lambda: _frame_records(
                client.stock_zt_pool_dtgc_em(date=compact_trade_date)
            ),
        )
        return {
            "trade_date": iso_date(compact_trade_date),
            "limit_up_count": len(limit_up_rows),
            "limit_down_count": len(limit_down_rows),
            "source": self.provider_name,
        }

    def health_check(self) -> dict[str, Any]:
        started = perf_counter()
        endpoint = "stock_board_concept_name_em"
        try:
            rows = self.fetch_sector_data()
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

    def _client(self) -> Any:
        client = self.quote_provider.client or self.quote_provider._load_client()
        if client is None:
            raise RuntimeError("akshare is not installed in the current environment")
        return client


def _frame_records(frame: Any) -> list[dict[str, Any]]:
    rows = frame.to_dict("records")
    if not isinstance(rows, list):
        raise ValueError("AKShare response must convert to a record list")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _daily_bar_from_akshare_row(
    *,
    row: dict[str, Any],
    symbol_hint: str | None,
) -> dict[str, Any]:
    return DailyBar(
        symbol=str(row.get("股票代码") or row.get("代码") or symbol_hint or ""),
        trade_date=iso_date(row.get("日期") or row.get("trade_date")),
        open=as_float(row.get("开盘")),
        high=as_float(row.get("最高")),
        low=as_float(row.get("最低")),
        close=as_float(row.get("收盘")),
        pre_close=_previous_close(
            close=as_float(row.get("收盘")),
            change_amount=as_float(row.get("涨跌额")),
        ),
        volume=as_float(row.get("成交量")),
        amount=as_float(row.get("成交额")),
        turnover_rate=as_float(row.get("换手率")),
        source=AKSHARE_PROVIDER_NAME,
    ).to_dict()


def _sector_from_akshare_row(
    *,
    row: dict[str, Any],
    trade_date: str | None,
) -> dict[str, Any]:
    return SectorSnapshot(
        sector_code=_optional_text(row.get("代码") or row.get("板块代码")),
        sector_name=str(row.get("板块名称") or row.get("名称") or ""),
        trade_date=iso_date(trade_date) if trade_date else None,
        pct_change=as_float(row.get("涨跌幅")),
        turnover_rate=as_float(row.get("换手率")),
        amount=as_float(row.get("成交额")),
        source=AKSHARE_PROVIDER_NAME,
    ).to_dict()


def _previous_close(
    *,
    close: float | None,
    change_amount: float | None,
) -> float | None:
    if close is None or change_amount is None:
        return None
    return round(close - change_amount, 4)


def _optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _compact_date(value: str) -> str:
    return value.replace("-", "")


def _schema_fingerprint(rows: list[dict[str, Any]]) -> str:
    keys = sorted({key for row in rows for key in row})
    return hashlib.sha256(",".join(keys).encode("utf-8")).hexdigest()
