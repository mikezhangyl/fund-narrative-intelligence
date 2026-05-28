from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from src.market_data.providers.akshare import AkShareMarketDataProvider
from src.market_data.providers.local_gateway import (
    GatewayJobTerminalError,
    LocalGatewayMarketDataProvider,
)
from src.market_data.providers.tushare import TushareMarketDataProvider
from src.market_data.request_logging import utc_now_iso
from src.market_data.validators import validate_records
from src.providers.eastmoney_market import EastmoneyMarketDataProvider


@dataclass(frozen=True)
class LiveValidationPlan:
    stock_codes: list[str]
    tushare_symbols: list[str]
    index_symbols: list[str]
    etf_symbols: list[str]
    trade_date: str


class ConsolidatedMarketDataSource:
    def __init__(
        self,
        *,
        quote_provider: Any | None = None,
        tushare_provider: Any | None = None,
        akshare_provider: Any | None = None,
        gateway_provider: Any | None = None,
    ):
        self.quote_provider = quote_provider or EastmoneyMarketDataProvider()
        self.tushare_provider = tushare_provider or TushareMarketDataProvider()
        self.akshare_provider = akshare_provider or AkShareMarketDataProvider()
        self.gateway_provider = gateway_provider or LocalGatewayMarketDataProvider.from_env()
        self.degradation_events: list[dict[str, str]] = []

    def fetch_latest_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        if self.gateway_provider is not None:
            try:
                return dict(self.gateway_provider.fetch_latest_stock_quotes(stock_codes))
            except Exception as exc:
                self.degradation_events.append(
                    {
                        "type": "provider_fallback",
                        "capability": "latest_stock_quotes",
                        "primary_provider": _provider_name(self.gateway_provider),
                        "fallback_provider": _provider_name(self.quote_provider),
                        "reason": str(exc),
                    }
                )
        return _call_quote_provider(self.quote_provider, stock_codes)

    def fetch_stock_metadata(self) -> list[dict[str, Any]]:
        return self._first_success(
            capability="stock_metadata",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_stock_metadata(),
                ),
                ProviderCall(
                    provider=self.tushare_provider,
                    call=lambda: self.tushare_provider.fetch_stock_metadata(),
                )
            ],
        )

    def fetch_daily_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        include_turnover: bool = True,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="daily_bars",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_daily_bars(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                        include_turnover=include_turnover,
                    ),
                ),
                ProviderCall(
                    provider=self.tushare_provider,
                    call=lambda: self.tushare_provider.fetch_daily_bars(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                        include_turnover=include_turnover,
                    ),
                ),
                ProviderCall(
                    provider=self.akshare_provider,
                    call=lambda: self.akshare_provider.fetch_daily_bars(
                        symbols=[_plain_symbol(symbol) for symbol in symbols],
                        start_date=start_date,
                        end_date=end_date,
                        include_turnover=include_turnover,
                    ),
                ),
            ],
        )

    def fetch_breadth_window_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        lookback_trading_days: int,
        include_turnover: bool = True,
    ) -> list[dict[str, Any]]:
        if self.gateway_provider is not None and hasattr(
            self.gateway_provider, "fetch_breadth_window_bars"
        ):
            try:
                return list(
                    self.gateway_provider.fetch_breadth_window_bars(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                        lookback_trading_days=lookback_trading_days,
                        include_turnover=include_turnover,
                    )
                )
            except GatewayJobTerminalError as exc:
                self.degradation_events.append(
                    {
                        "type": "provider_terminal_failure",
                        "capability": "breadth_window_bars",
                        "primary_provider": _provider_name(self.gateway_provider),
                        "fallback_provider": "",
                        "reason": str(exc),
                    }
                )
                raise
            except Exception as exc:
                self.degradation_events.append(
                    {
                        "type": "provider_fallback",
                        "capability": "breadth_window_bars",
                        "primary_provider": _provider_name(self.gateway_provider),
                        "fallback_provider": "daily_bars",
                        "reason": str(exc),
                    }
                )
        return self.fetch_daily_bars(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            include_turnover=include_turnover,
        )

    def fetch_index_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="index_bars",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_index_bars(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                ),
                ProviderCall(
                    provider=self.tushare_provider,
                    call=lambda: self.tushare_provider.fetch_index_bars(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                )
            ],
        )

    def fetch_trade_calendar(
        self,
        *,
        exchange: str = "SSE",
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="trade_calendar",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_trade_calendar(
                        exchange=exchange,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                ),
                ProviderCall(
                    provider=self.tushare_provider,
                    call=lambda: self.tushare_provider.fetch_trade_calendar(
                        exchange=exchange,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                )
            ],
        )

    def fetch_etf_data(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="etf_data",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_etf_data(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                ),
                ProviderCall(
                    provider=self.tushare_provider,
                    call=lambda: self.tushare_provider.fetch_etf_data(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                    ),
                ),
                ProviderCall(
                    provider=self.akshare_provider,
                    call=lambda: self.akshare_provider.fetch_etf_data(
                        symbols=[_plain_symbol(symbol) for symbol in symbols],
                        start_date=start_date,
                        end_date=end_date,
                    ),
                ),
            ],
        )

    def fetch_etf_spot(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._first_success(
            capability="etf_spot",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_etf_spot(limit=limit),
                )
            ],
        )

    def fetch_sector_data(
        self,
        *,
        trade_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="sector_data",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_sector_data(
                        trade_date=trade_date,
                        limit=limit,
                    ),
                ),
                ProviderCall(
                    provider=self.akshare_provider,
                    call=lambda: self.akshare_provider.fetch_sector_data(
                        trade_date=trade_date
                    ),
                )
            ],
        )

    def fetch_limit_up_down_stats(self, *, trade_date: str) -> dict[str, Any]:
        rows = self._first_success(
            capability="limit_up_down_stats",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: [self.gateway_provider.fetch_limit_up_down_stats(
                        trade_date=trade_date
                    )],
                ),
                ProviderCall(
                    provider=self.akshare_provider,
                    call=lambda: [self.akshare_provider.fetch_limit_up_down_stats(
                        trade_date=trade_date
                    )],
                )
            ],
        )
        return rows[0] if rows else {}

    def fetch_news_briefs(
        self,
        *,
        start_datetime: str,
        end_datetime: str,
        source_provider: str = "tushare",
        src: str = "sina",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="news_briefs",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_news_briefs(
                        source_provider=source_provider,
                        src=src,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_northbound_capital(self, *, trade_date: str) -> dict[str, Any]:
        rows = self._first_success(
            capability="northbound_capital",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: [self.gateway_provider.fetch_northbound_capital(
                        trade_date=trade_date
                    )],
                )
            ],
        )
        return rows[0] if rows else {}

    def fetch_main_capital_flow(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="main_capital_flow",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_main_capital_flow(
                        trade_date=trade_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_etf_flow(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="etf_flow",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_etf_flow(
                        trade_date=trade_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_dragon_tiger(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="dragon_tiger_list",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_dragon_tiger(
                        trade_date=trade_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_sector_constituents(
        self,
        *,
        sector_name: str,
        trade_date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="sector_constituents",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_sector_constituents(
                        sector_name=sector_name,
                        trade_date=trade_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_etf_basic(
        self,
        *,
        market: str = "cn",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="etf_basic",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_etf_basic(
                        market=market,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_index_constituents(
        self,
        *,
        index_symbol: str,
        trade_date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="index_constituents",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_index_constituents(
                        index_symbol=index_symbol,
                        trade_date=trade_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_margin_summary(self, *, trade_date: str) -> dict[str, Any]:
        rows = self._first_success(
            capability="margin_summary",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: [self.gateway_provider.fetch_margin_summary(
                        trade_date=trade_date
                    )],
                )
            ],
        )
        return rows[0] if rows else {}

    def fetch_margin_detail(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="margin_detail",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_margin_detail(
                        trade_date=trade_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_earnings_calendar(
        self,
        *,
        start_date: str,
        end_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="earnings_calendar",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_earnings_calendar(
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit,
                    ),
                )
            ],
        )

    def fetch_cyq_chips(
        self,
        *,
        symbols: list[str],
        trade_date: str,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="cyq_chips",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_cyq_chips(
                        symbols=symbols,
                        trade_date=trade_date,
                    ),
                )
            ],
        )

    def fetch_stock_sector_memberships(
        self,
        *,
        symbols: list[str],
        trade_date: str | None = None,
        sector_types: list[str] | None = None,
        limit_per_symbol: int = 50,
        sector_universe_limit: int | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._first_success(
            capability="stock_sector_membership",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_stock_sector_memberships(
                        symbols=symbols,
                        trade_date=trade_date,
                        sector_types=sector_types or ["concept"],
                        limit_per_symbol=limit_per_symbol,
                        sector_universe_limit=sector_universe_limit,
                    ),
                )
            ],
        )
        event = _gateway_meta_degradation_event(
            capability="stock_sector_membership",
            provider=self.gateway_provider,
            meta=getattr(self.gateway_provider, "last_stock_sector_membership_meta", None),
        )
        if event is not None:
            self.degradation_events.append(event)
        return rows

    def fetch_fund_profile(self, *, fund_code: str) -> list[dict[str, Any]]:
        return self._first_success(
            capability="fund_profile",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_fund_profile(
                        fund_code=fund_code,
                    ),
                )
            ],
        )

    def fetch_fund_holdings(
        self,
        *,
        fund_code: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self._first_success(
            capability="fund_holdings",
            calls=[
                *_gateway_calls(
                    self.gateway_provider,
                    lambda: self.gateway_provider.fetch_fund_holdings(
                        fund_code=fund_code,
                        limit=limit,
                    ),
                )
            ],
        )

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": "consolidated-market-data-source",
            "checked_at": utc_now_iso(),
            "providers": {
                "gateway": _safe_health(self.gateway_provider)
                if self.gateway_provider is not None
                else {"provider": "local-market-data-gateway", "ok": None},
                "quote": _safe_health(self.quote_provider),
                "tushare": _safe_health(self.tushare_provider),
                "akshare": _safe_health(self.akshare_provider),
            },
        }

    def run_live_validation(self, plan: LiveValidationPlan) -> dict[str, Any]:
        checks = [
            self._validate_payload(
                capability="latest_stock_quotes",
                source_name=_provider_name(self.quote_provider),
                endpoint="get_stock_quotes",
                required_fields={"stock_code", "latest_price", "retrieved_at"},
                operation=lambda: _quote_rows(
                    self.fetch_latest_stock_quotes(plan.stock_codes)
                ),
            ),
            self._validate_payload(
                capability="daily_bars",
                source_name="tushare_or_akshare",
                endpoint="daily_bars",
                required_fields={"symbol", "trade_date", "close", "volume"},
                operation=lambda: self.fetch_daily_bars(
                    symbols=plan.tushare_symbols,
                    start_date=plan.trade_date,
                    end_date=plan.trade_date,
                    include_turnover=True,
                ),
            ),
            self._validate_payload(
                capability="index_bars",
                source_name=_provider_name(self.tushare_provider),
                endpoint="index_daily",
                required_fields={"symbol", "trade_date", "close"},
                operation=lambda: self.fetch_index_bars(
                    symbols=plan.index_symbols,
                    start_date=plan.trade_date,
                    end_date=plan.trade_date,
                ),
            ),
            self._validate_payload(
                capability="trade_calendar",
                source_name=_provider_name(self.tushare_provider),
                endpoint="trade_cal",
                required_fields={"exchange", "cal_date", "is_open"},
                operation=lambda: self.fetch_trade_calendar(
                    exchange="SSE",
                    start_date=plan.trade_date,
                    end_date=plan.trade_date,
                ),
            ),
            self._validate_payload(
                capability="etf_data",
                source_name="tushare_or_akshare",
                endpoint="etf_daily",
                required_fields={"symbol", "trade_date", "close"},
                operation=lambda: self.fetch_etf_data(
                    symbols=plan.etf_symbols,
                    start_date=plan.trade_date,
                    end_date=plan.trade_date,
                ),
            ),
            self._validate_payload(
                capability="sector_data",
                source_name=_provider_name(self.akshare_provider),
                endpoint="stock_board_concept_name_em",
                required_fields={"sector_name", "pct_change", "source"},
                operation=lambda: self.fetch_sector_data(trade_date=plan.trade_date),
            ),
            self._validate_payload(
                capability="limit_up_down_stats",
                source_name=_provider_name(self.akshare_provider),
                endpoint="stock_zt_pool",
                required_fields={"trade_date", "limit_up_count", "limit_down_count"},
                operation=lambda: [
                    self.fetch_limit_up_down_stats(trade_date=plan.trade_date)
                ],
            ),
        ]
        return {
            "version": "market-data-live-validation-v1",
            "generated_at": utc_now_iso(),
            "checks": checks,
            "summary": _summary(checks),
            "degradation_events": list(self.degradation_events),
        }

    def _validate_payload(
        self,
        *,
        capability: str,
        source_name: str,
        endpoint: str,
        required_fields: set[str],
        operation: Callable[[], list[dict[str, Any]]],
    ) -> dict[str, Any]:
        started = perf_counter()
        try:
            rows = operation()
            latency_ms = round((perf_counter() - started) * 1000, 3)
            result = validate_records(
                source=source_name,
                endpoint=endpoint,
                records=rows,
                required_fields=required_fields,
                latency_ms=latency_ms,
            ).to_dict()
            result["capability"] = capability
            result["row_count"] = len(rows)
            return result
        except Exception as exc:
            latency_ms = round((perf_counter() - started) * 1000, 3)
            result = validate_records(
                source=source_name,
                endpoint=endpoint,
                records=[],
                required_fields=required_fields,
                latency_ms=latency_ms,
                failure_reason=str(exc),
            ).to_dict()
            result["capability"] = capability
            result["row_count"] = 0
            return result

    def _first_success(
        self,
        *,
        capability: str,
        calls: list["ProviderCall"],
    ) -> list[dict[str, Any]]:
        failures: list[str] = []
        for index, provider_call in enumerate(calls):
            try:
                return provider_call.call()
            except Exception as exc:
                failures.append(f"{_provider_name(provider_call.provider)}: {exc}")
                if index + 1 < len(calls):
                    self.degradation_events.append(
                        {
                            "type": "provider_fallback",
                            "capability": capability,
                            "primary_provider": _provider_name(provider_call.provider),
                            "fallback_provider": _provider_name(calls[index + 1].provider),
                            "reason": str(exc),
                        }
                    )
        raise RuntimeError(
            f"No provider succeeded for {capability}: {'; '.join(failures)}"
        )


@dataclass(frozen=True)
class ProviderCall:
    provider: Any
    call: Callable[[], list[dict[str, Any]]]


def _gateway_calls(
    gateway_provider: Any | None,
    call: Callable[[], list[dict[str, Any]]],
) -> list[ProviderCall]:
    if gateway_provider is None:
        return []
    return [ProviderCall(provider=gateway_provider, call=call)]


def _gateway_meta_degradation_event(
    *,
    capability: str,
    provider: Any | None,
    meta: Any,
) -> dict[str, str] | None:
    if provider is None or not isinstance(meta, dict):
        return None
    warning = meta.get("warning")
    status = str(meta.get("status") or "")
    if not isinstance(warning, dict) and status not in {"degraded", "error"}:
        return None
    code = ""
    message = ""
    if isinstance(warning, dict):
        code = str(warning.get("code") or "").strip()
        message = str(warning.get("message") or "").strip()
    reason = ": ".join(part for part in (code, message) if part)
    if not reason:
        reason = status or "gateway response degraded"
    return {
        "type": "provider_degraded",
        "capability": capability,
        "primary_provider": _provider_name(provider),
        "fallback_provider": "",
        "reason": reason,
    }


def default_live_validation_plan(*, trade_date: str) -> LiveValidationPlan:
    return LiveValidationPlan(
        stock_codes=["600519"],
        tushare_symbols=["600519.SH"],
        index_symbols=["000001.SH"],
        etf_symbols=["510300.SH"],
        trade_date=trade_date,
    )


def _call_quote_provider(provider: Any, stock_codes: list[str]) -> dict[str, Any]:
    if callable(getattr(provider, "get_stock_quotes", None)):
        return dict(provider.get_stock_quotes(stock_codes))
    if callable(getattr(provider, "fetch_latest_stock_quotes", None)):
        return dict(provider.fetch_latest_stock_quotes(stock_codes))
    raise AttributeError(f"{_provider_name(provider)} does not support stock quotes")


def _quote_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("quotes")
    if not isinstance(rows, list):
        raise ValueError("quote payload missing quotes list")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _safe_health(provider: Any) -> dict[str, Any]:
    health_check = getattr(provider, "health_check", None)
    if not callable(health_check):
        return {"provider": _provider_name(provider), "ok": None}
    try:
        return dict(health_check())
    except Exception as exc:
        return {"provider": _provider_name(provider), "ok": False, "error": str(exc)}


def _summary(checks: list[dict[str, Any]]) -> dict[str, int]:
    available = sum(1 for check in checks if check.get("availability") is True)
    return {
        "total_checks": len(checks),
        "available_checks": available,
        "failed_checks": len(checks) - available,
    }


def _provider_name(provider: Any) -> str:
    return str(getattr(provider, "provider_name", provider.__class__.__name__))


def _plain_symbol(symbol: str) -> str:
    return str(symbol).split(".", 1)[0]
