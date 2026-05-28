from __future__ import annotations

import json
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from src import local_env
from src.market_data.gateway_contract import rows_from_path

LOCAL_GATEWAY_PROVIDER_NAME = "local-market-data-gateway"
DEFAULT_GATEWAY_BASE_URL_ENV = "MARKET_DATA_GATEWAY_URL"
DEFAULT_GATEWAY_TIMEOUT_SECONDS_ENV = "MARKET_DATA_GATEWAY_TIMEOUT_SECONDS"
DEFAULT_ASYNC_DAILY_BARS_THRESHOLD_ENV = (
    "MARKET_DATA_GATEWAY_ASYNC_DAILY_BARS_THRESHOLD"
)
DEFAULT_ASYNC_DAILY_BARS_MAX_WAIT_ENV = (
    "MARKET_DATA_GATEWAY_ASYNC_DAILY_BARS_MAX_WAIT_SECONDS"
)
DEFAULT_ASYNC_DAILY_BARS_POLL_INTERVAL_ENV = (
    "MARKET_DATA_GATEWAY_ASYNC_DAILY_BARS_POLL_INTERVAL_SECONDS"
)
DEFAULT_ASYNC_DAILY_BARS_THRESHOLD = 100
DEFAULT_ASYNC_DAILY_BARS_MAX_WAIT_SECONDS = 900.0
DEFAULT_ASYNC_DAILY_BARS_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_ASYNC_DAILY_BARS_BATCH_SIZE = 100
DEFAULT_ASYNC_DAILY_BARS_ROWS_PAGE_SIZE = 50_000
JOB_TERMINAL_STATUSES = {
    "completed",
    "completed_with_failures",
    "failed",
    "cancelled",
    "interrupted",
}

GatewayHttpFetcher = Callable[
    [str, str, dict[str, Any] | None, float],
    tuple[int, dict[str, Any]],
]


class GatewayJobTerminalError(RuntimeError):
    pass


class LocalGatewayMarketDataProvider:
    provider_name = LOCAL_GATEWAY_PROVIDER_NAME

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        fetcher: GatewayHttpFetcher | None = None,
        async_daily_bars_threshold: int | None = None,
        job_max_wait_seconds: float | None = None,
        job_poll_interval_seconds: float | None = None,
        job_rows_page_size: int = DEFAULT_ASYNC_DAILY_BARS_ROWS_PAGE_SIZE,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.fetcher = fetcher or _http_fetch
        self.async_daily_bars_threshold = (
            async_daily_bars_threshold
            if async_daily_bars_threshold is not None
            else _int_config(
                DEFAULT_ASYNC_DAILY_BARS_THRESHOLD_ENV,
                DEFAULT_ASYNC_DAILY_BARS_THRESHOLD,
            )
        )
        self.job_max_wait_seconds = (
            job_max_wait_seconds
            if job_max_wait_seconds is not None
            else _float_config(
                DEFAULT_ASYNC_DAILY_BARS_MAX_WAIT_ENV,
                DEFAULT_ASYNC_DAILY_BARS_MAX_WAIT_SECONDS,
            )
        )
        self.job_poll_interval_seconds = (
            job_poll_interval_seconds
            if job_poll_interval_seconds is not None
            else _float_config(
                DEFAULT_ASYNC_DAILY_BARS_POLL_INTERVAL_ENV,
                DEFAULT_ASYNC_DAILY_BARS_POLL_INTERVAL_SECONDS,
            )
        )
        self.job_rows_page_size = max(1, job_rows_page_size)
        self.last_daily_bars_job: dict[str, Any] | None = None
        self.last_breadth_window_job: dict[str, Any] | None = None
        self.last_stock_sector_membership_meta: dict[str, Any] | None = None

    @classmethod
    def from_env(cls) -> "LocalGatewayMarketDataProvider | None":
        base_url = local_env.get_config_value(DEFAULT_GATEWAY_BASE_URL_ENV)
        if not base_url:
            return None
        return cls(
            base_url=base_url,
            timeout_seconds=_float_config(DEFAULT_GATEWAY_TIMEOUT_SECONDS_ENV, 10.0),
        )

    def fetch_latest_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        rows = self._rows(
            method="GET",
            path="/api/v1/market-data/eastmoney/market-quotes",
            query={"stock_codes": ",".join(stock_codes)},
        )
        found_codes = {str(row.get("stock_code") or "") for row in rows}
        return {
            "provider_name": self.provider_name,
            "quotes": rows,
            "missing_stock_codes": [
                code for code in stock_codes if str(code) not in found_codes
            ],
        }

    def fetch_stock_metadata(self) -> list[dict[str, Any]]:
        return self._rows(
            method="POST",
            path="/api/v1/market-data/tushare/stock-basic",
            json_body={"list_status": "L"},
        )

    def fetch_daily_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        include_turnover: bool = True,
    ) -> list[dict[str, Any]]:
        if self._should_use_daily_bars_job(symbols):
            return self._fetch_daily_bars_via_job(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                include_turnover=include_turnover,
            )
        return self._rows(
            method="POST",
            path="/api/v1/market-data/tushare/daily",
            json_body={
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "include_turnover": include_turnover,
            },
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
        del start_date
        create_payload = self._request(
            method="POST",
            path="/api/v1/market-data/jobs/breadth-window",
            json_body={
                "provider": "tushare",
                "symbols": symbols,
                "end_date": end_date,
                "lookback_trading_days": lookback_trading_days,
                "include_turnover": include_turnover,
                "mode": "read_through_cache",
                "allow_stale": True,
            },
        )
        job_id = _path_value(create_payload, "data.job_id")
        if not job_id:
            raise RuntimeError("gateway breadth-window job response missing data.job_id")
        status_payload = self._wait_for_job(str(job_id), job_label="breadth-window")
        self.last_breadth_window_job = dict(status_payload)
        return self._rows_for_terminal_job(
            job_id=str(job_id),
            status_payload=status_payload,
            job_label="breadth-window",
        )

    def fetch_index_bars(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="POST",
            path="/api/v1/market-data/tushare/index-daily",
            json_body={"symbols": symbols, "start_date": start_date, "end_date": end_date},
        )

    def fetch_trade_calendar(
        self,
        *,
        exchange: str = "SSE",
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="POST",
            path="/api/v1/market-data/tushare/trade-cal",
            json_body={
                "exchange": exchange,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

    def fetch_etf_data(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="POST",
            path="/api/v1/market-data/tushare/fund-daily",
            json_body={"symbols": symbols, "start_date": start_date, "end_date": end_date},
        )

    def fetch_etf_spot(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/etf/spot",
            query={"limit": limit},
        )

    def fetch_sector_data(
        self,
        *,
        trade_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"limit": limit}
        if trade_date:
            query = {**query, "trade_date": trade_date}
        return self._rows(
            method="GET",
            path="/api/v1/market-data/sectors/concepts",
            query=query,
        )

    def fetch_limit_up_down_stats(self, *, trade_date: str) -> dict[str, Any]:
        rows = self._rows(
            method="GET",
            path="/api/v1/market-data/market/limit-up-down",
            query={"trade_date": trade_date},
        )
        return rows[0] if rows else {}

    def fetch_news_briefs(
        self,
        *,
        source_provider: str,
        src: str,
        start_datetime: str,
        end_datetime: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="POST",
            path="/api/v1/market-data/news/briefs",
            json_body={
                "source_provider": source_provider,
                "src": src,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "limit": limit,
            },
        )

    def fetch_northbound_capital(self, *, trade_date: str) -> dict[str, Any]:
        rows = self._rows(
            method="GET",
            path="/api/v1/market-data/capital/northbound",
            query={"trade_date": trade_date},
        )
        return rows[0] if rows else {}

    def fetch_main_capital_flow(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/capital/main-flow",
            query={"trade_date": trade_date, "limit": limit},
        )

    def fetch_etf_flow(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/etf/flow",
            query={"trade_date": trade_date, "limit": limit},
        )

    def fetch_dragon_tiger(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/market/dragon-tiger",
            query={"trade_date": trade_date, "limit": limit},
        )

    def fetch_sector_constituents(
        self,
        *,
        sector_name: str,
        trade_date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"sector_name": sector_name, "limit": limit}
        if trade_date:
            query = {**query, "trade_date": trade_date}
        return self._rows(
            method="GET",
            path="/api/v1/market-data/sectors/constituents",
            query=query,
        )

    def fetch_etf_basic(
        self,
        *,
        market: str = "cn",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/etf/basic",
            query={"market": market, "limit": limit},
        )

    def fetch_index_constituents(
        self,
        *,
        index_symbol: str,
        trade_date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"index_symbol": index_symbol, "limit": limit}
        if trade_date:
            query = {**query, "trade_date": trade_date}
        return self._rows(
            method="GET",
            path="/api/v1/market-data/index/constituents",
            query=query,
        )

    def fetch_margin_summary(self, *, trade_date: str) -> dict[str, Any]:
        rows = self._rows(
            method="GET",
            path="/api/v1/market-data/margin/summary",
            query={"trade_date": trade_date},
        )
        return rows[0] if rows else {}

    def fetch_margin_detail(
        self,
        *,
        trade_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/margin/detail",
            query={"trade_date": trade_date, "limit": limit},
        )

    def fetch_earnings_calendar(
        self,
        *,
        start_date: str,
        end_date: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/fundamentals/earnings-calendar",
            query={"start_date": start_date, "end_date": end_date, "limit": limit},
        )

    def fetch_cyq_chips(
        self,
        *,
        symbols: list[str],
        trade_date: str,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="POST",
            path="/api/v1/market-data/chips/cyq",
            json_body={"symbols": symbols, "trade_date": trade_date},
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
        body: dict[str, Any] = {
            "symbols": symbols,
            "sector_types": sector_types or ["concept"],
            "limit_per_symbol": limit_per_symbol,
        }
        if sector_universe_limit is not None:
            body = {**body, "sector_universe_limit": sector_universe_limit}
        if trade_date:
            body = {**body, "trade_date": trade_date}
        payload = self._request(
            method="POST",
            path="/api/v1/market-data/stocks/sector-memberships",
            json_body=body,
        )
        meta = payload.get("meta") if isinstance(payload, dict) else None
        self.last_stock_sector_membership_meta = dict(meta) if isinstance(meta, dict) else None
        return rows_from_path(payload, "data.rows")

    def fetch_fund_profile(self, *, fund_code: str) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/funds/profile",
            query={"fund_code": fund_code},
        )

    def fetch_fund_holdings(
        self,
        *,
        fund_code: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return self._rows(
            method="GET",
            path="/api/v1/market-data/funds/holdings",
            query={"fund_code": fund_code, "limit": limit},
        )

    def _rows(
        self,
        *,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        status, payload = self.fetcher(
            method,
            _url(base_url=self.base_url, path=path, query=query),
            json_body,
            self.timeout_seconds,
        )
        if status < 200 or status >= 300:
            raise RuntimeError(_gateway_error_message(status, payload))
        return rows_from_path(payload, "data.rows")

    def _should_use_daily_bars_job(self, symbols: list[str]) -> bool:
        return self.async_daily_bars_threshold > 0 and len(symbols) >= self.async_daily_bars_threshold

    def _fetch_daily_bars_via_job(
        self,
        *,
        symbols: list[str],
        start_date: str,
        end_date: str,
        include_turnover: bool,
    ) -> list[dict[str, Any]]:
        create_payload = self._request(
            method="POST",
            path="/api/v1/market-data/jobs/daily-bars",
            json_body={
                "provider": "tushare",
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "include_turnover": include_turnover,
                "mode": "read_through_cache",
                "allow_stale": True,
                "force_refresh": False,
                "batch_size": DEFAULT_ASYNC_DAILY_BARS_BATCH_SIZE,
            },
        )
        job_id = _path_value(create_payload, "data.job_id")
        if not job_id:
            raise RuntimeError("gateway daily-bars job response missing data.job_id")
        status_payload = self._wait_for_job(str(job_id), job_label="daily-bars")
        self.last_daily_bars_job = dict(status_payload)
        return self._rows_for_terminal_job(
            job_id=str(job_id),
            status_payload=status_payload,
            job_label="daily-bars",
        )

    def _wait_for_job(self, job_id: str, *, job_label: str) -> dict[str, Any]:
        deadline = time.monotonic() + max(0.0, self.job_max_wait_seconds)
        latest: dict[str, Any] = {}
        while True:
            payload = self._request(
                method="GET",
                path=f"/api/v1/market-data/jobs/{job_id}",
            )
            latest = dict(_path_value(payload, "data") or {})
            status = str(latest.get("status") or "")
            if status in JOB_TERMINAL_STATUSES:
                return latest
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"gateway {job_label} job {job_id} did not finish within "
                    f"{self.job_max_wait_seconds} seconds; latest status: {latest}"
                )
            if self.job_poll_interval_seconds > 0:
                time.sleep(self.job_poll_interval_seconds)

    def _rows_for_terminal_job(
        self,
        *,
        job_id: str,
        status_payload: dict[str, Any],
        job_label: str,
    ) -> list[dict[str, Any]]:
        status = str(status_payload.get("status") or "")
        if status in {"failed", "cancelled", "interrupted"}:
            raise GatewayJobTerminalError(
                f"gateway {job_label} job ended with "
                f"{status}: {_compact_failures(status_payload.get('failures'))}"
            )
        rows = self._fetch_job_rows(job_id)
        if status == "completed_with_failures" and not rows:
            raise RuntimeError(
                f"gateway {job_label} job completed with failures and no rows: "
                f"{_compact_failures(status_payload.get('failures'))}"
            )
        return rows

    def _fetch_job_rows(self, job_id: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = self._request(
                method="GET",
                path=f"/api/v1/market-data/jobs/{job_id}/rows",
                query={"offset": offset, "limit": self.job_rows_page_size},
            )
            page_rows = rows_from_path(payload, "data.rows")
            rows.extend(page_rows)
            pagination = _path_value(payload, "meta.pagination") or {}
            returned = int(pagination.get("returned", len(page_rows)))
            total = pagination.get("total")
            offset += returned
            if returned <= 0:
                return rows
            if total is not None and offset >= int(total):
                return rows
            if len(page_rows) < self.job_rows_page_size and total is None:
                return rows

    def _request(
        self,
        *,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        status, payload = self.fetcher(
            method,
            _url(base_url=self.base_url, path=path, query=query),
            json_body,
            self.timeout_seconds,
        )
        if status < 200 or status >= 300:
            raise RuntimeError(_gateway_error_message(status, payload))
        return payload


def _url(*, base_url: str, path: str, query: dict[str, Any] | None = None) -> str:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    if query:
        return f"{url}?{urlencode(query)}"
    return url


def _http_fetch(
    method: str,
    url: str,
    json_body: dict[str, Any] | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": {"code": "http_error", "message": str(exc)}}
        return int(exc.code), payload
    except (OSError, URLError) as exc:
        raise RuntimeError(f"gateway request failed: {exc}") from exc


def _gateway_error_message(status: int, payload: dict[str, Any]) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        code = str(error.get("code") or "UNKNOWN_GATEWAY_ERROR")
        message = str(error.get("message") or "")
        return f"gateway returned HTTP {status}: {code}: {message}"
    return f"gateway returned HTTP {status}"


def _path_value(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _compact_failures(value: Any) -> str:
    if not value:
        return "none"
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def _int_config(name: str, default: int) -> int:
    value = local_env.get_config_value(name)
    if value is None:
        return default
    try:
        return max(0, int(value))
    except ValueError:
        return default


def _float_config(name: str, default: float) -> float:
    value = local_env.get_config_value(name)
    if value is None:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        return default
