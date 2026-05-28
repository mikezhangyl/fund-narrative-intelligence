from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import local_env
from src.providers.security_market import (
    resolve_security_market,
    tushare_a_share_ts_code,
)
from src.providers.tushare_common import (
    TUSHARE_API_URL,
    TushareFetcher,
    as_float,
    get_tushare_api_url,
    query_tushare_rows,
    stock_basic_metadata,
)
from src.validation import validate_market_quote_payload

TUSHARE_MARKET_QUOTE_PROVIDER = "tushare-market-quote"
TUSHARE_MARKET_QUOTE_VERSION = "tushare-market-quote-v1"
_DAILY_FIELDS = ",".join(
    [
        "ts_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    ]
)


class TushareMarketDataProvider:
    provider_name = TUSHARE_MARKET_QUOTE_PROVIDER
    provider_version = TUSHARE_MARKET_QUOTE_VERSION
    source_url = TUSHARE_API_URL

    def __init__(
        self,
        token: str | None = None,
        fetcher: TushareFetcher | None = None,
    ):
        self.token = (
            token if token is not None else local_env.get_config_value("TUSHARE_TOKEN")
        )
        self.fetcher = fetcher
        self.source_url = get_tushare_api_url()
        self.degradation_events: list[dict[str, str]] = []

    def get_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if not self.token:
            self.degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider": self.provider_name,
                    "reason": "TUSHARE_TOKEN is not configured",
                }
            )
            return _unavailable_payload(stock_codes=stock_codes, retrieved_at=retrieved_at)

        quotes: list[dict[str, Any]] = []
        failed_stock_codes: list[str] = []
        for stock_code in stock_codes:
            market = resolve_security_market(stock_code)
            ts_code = tushare_a_share_ts_code(stock_code)
            if market not in {"sh", "sz"} or ts_code is None:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unsupported_market",
                        "provider": self.provider_name,
                        "reason": (
                            "Tushare market quotes currently support A-share stock codes only: "
                            f"{stock_code}"
                        ),
                    }
                )
                continue
            try:
                quotes.append(
                    _build_quote(
                        stock_code=str(stock_code),
                        ts_code=ts_code,
                        token=self.token,
                        fetcher=self.fetcher,
                        retrieved_at=retrieved_at,
                    )
                )
            except Exception as exc:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider": self.provider_name,
                        "reason": f"Tushare market quote fetch failed for {stock_code}: {exc}",
                    }
                )

        payload = {
            "version": TUSHARE_MARKET_QUOTE_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(quotes, failed_stock_codes),
            "source_url": self.source_url,
            "retrieved_at": retrieved_at,
            "quotes": quotes,
            "missing_stock_codes": sorted(set(failed_stock_codes)),
        }
        validate_market_quote_payload(payload)
        return payload


def _build_quote(
    *,
    stock_code: str,
    ts_code: str,
    token: str,
    fetcher: TushareFetcher | None,
    retrieved_at: str,
) -> dict[str, Any]:
    rows = query_tushare_rows(
        token=token,
        api_name="daily",
        params={"ts_code": ts_code},
        fields=_DAILY_FIELDS,
        fetcher=fetcher,
    )
    if not rows:
        raise ValueError(f"No Tushare daily rows returned for {ts_code}")
    row = max(rows, key=lambda item: str(item.get("trade_date") or ""))
    metadata = stock_basic_metadata(
        ts_code=ts_code,
        token=token,
        fetcher=fetcher,
    )
    return {
        "stock_code": stock_code,
        "stock_name": str(metadata.get("stock_name") or stock_code),
        "source_provider": TUSHARE_MARKET_QUOTE_PROVIDER,
        "source_url": get_tushare_api_url(),
        "latest_price": as_float(row.get("close")),
        "change_percent": as_float(row.get("pct_chg")),
        "change_amount": as_float(row.get("change")),
        "volume": as_float(row.get("vol")),
        "amount": as_float(row.get("amount")),
        "high": as_float(row.get("high")),
        "low": as_float(row.get("low")),
        "open": as_float(row.get("open")),
        "previous_close": as_float(row.get("pre_close")),
        "retrieved_at": retrieved_at,
    }


def _data_quality(
    quotes: list[dict[str, Any]],
    missing_stock_codes: list[str],
) -> str:
    if not quotes:
        return "unavailable"
    if missing_stock_codes:
        return "partial"
    return "fresh"


def _unavailable_payload(
    *,
    stock_codes: list[str],
    retrieved_at: str,
) -> dict[str, Any]:
    payload = {
        "version": TUSHARE_MARKET_QUOTE_VERSION,
        "provider_name": TUSHARE_MARKET_QUOTE_PROVIDER,
        "provider_version": TUSHARE_MARKET_QUOTE_VERSION,
        "data_quality": "unavailable",
        "source_url": get_tushare_api_url(),
        "retrieved_at": retrieved_at,
        "quotes": [],
        "missing_stock_codes": sorted(set(str(code) for code in stock_codes)),
    }
    validate_market_quote_payload(payload)
    return payload
