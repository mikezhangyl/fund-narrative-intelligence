from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from src.providers.security_market import (
    is_hong_kong_stock_code,
    resolve_security_market,
)
from src.validation import validate_market_quote_payload

AKSHARE_MARKET_QUOTE_PROVIDER = "akshare-market-quote"
AKSHARE_MARKET_QUOTE_VERSION = "akshare-market-quote-v1"
AKSHARE_SOURCE_URL = "https://akshare.akfamily.xyz/data/stock/stock.html"
AkshareClientLoader = Callable[[], Any]


class AkshareMarketDataProvider:
    provider_name = AKSHARE_MARKET_QUOTE_PROVIDER
    provider_version = AKSHARE_MARKET_QUOTE_VERSION
    source_url = AKSHARE_SOURCE_URL

    def __init__(
        self,
        client: Any | None = None,
        client_loader: AkshareClientLoader | None = None,
    ):
        self.client = client
        self.client_loader = client_loader or _load_akshare_client
        self.degradation_events: list[dict[str, str]] = []

    def get_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        client = self.client or self._load_client()
        if client is None:
            self.degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider": self.provider_name,
                    "reason": "akshare is not installed in the current environment",
                }
            )
            return _unavailable_payload(stock_codes=stock_codes, retrieved_at=retrieved_at)

        quotes: list[dict[str, Any]] = []
        failed_stock_codes: list[str] = []
        for stock_code in stock_codes:
            market = resolve_security_market(stock_code)
            if market not in {"sh", "sz"} or is_hong_kong_stock_code(stock_code):
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unsupported_market",
                        "provider": self.provider_name,
                        "reason": (
                            "AKShare market quotes currently support A-share stock codes only: "
                            f"{stock_code}"
                        ),
                    }
                )
                continue
            try:
                quotes.append(
                    _fetch_quote(
                        client=client,
                        stock_code=str(stock_code),
                        retrieved_at=retrieved_at,
                    )
                )
            except Exception as exc:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider": self.provider_name,
                        "reason": f"AKShare market quote fetch failed for {stock_code}: {exc}",
                    }
                )

        payload = {
            "version": self.provider_version,
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

    def _load_client(self) -> Any | None:
        try:
            return self.client_loader()
        except Exception as exc:
            self.degradation_events.append(
                {
                    "type": "provider_unavailable",
                    "provider": self.provider_name,
                    "reason": f"Failed to load akshare client: {exc}",
                }
            )
            return None


def _fetch_quote(
    *,
    client: Any,
    stock_code: str,
    retrieved_at: str,
) -> dict[str, Any]:
    end_date = date.today()
    start_date = end_date - timedelta(days=10)
    frame = client.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust="",
    )
    rows = frame.to_dict("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("AKShare returned no history rows")
    latest = rows[-1]
    close = _as_float(latest.get("收盘"))
    change_amount = _as_float(latest.get("涨跌额"))
    previous_close = _previous_close(close=close, change_amount=change_amount)
    return {
        "stock_code": str(latest.get("股票代码") or stock_code),
        "stock_name": str(latest.get("股票名称") or latest.get("名称") or stock_code),
        "source_provider": AKSHARE_MARKET_QUOTE_PROVIDER,
        "source_url": AKSHARE_SOURCE_URL,
        "latest_price": close,
        "change_percent": _as_float(latest.get("涨跌幅")),
        "change_amount": change_amount,
        "volume": _as_float(latest.get("成交量")),
        "amount": _as_float(latest.get("成交额")),
        "high": _as_float(latest.get("最高")),
        "low": _as_float(latest.get("最低")),
        "open": _as_float(latest.get("开盘")),
        "previous_close": previous_close,
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
        "version": AKSHARE_MARKET_QUOTE_VERSION,
        "provider_name": AKSHARE_MARKET_QUOTE_PROVIDER,
        "provider_version": AKSHARE_MARKET_QUOTE_VERSION,
        "data_quality": "unavailable",
        "source_url": AKSHARE_SOURCE_URL,
        "retrieved_at": retrieved_at,
        "quotes": [],
        "missing_stock_codes": sorted(set(str(code) for code in stock_codes)),
    }
    validate_market_quote_payload(payload)
    return payload


def _load_akshare_client() -> Any:
    import akshare  # type: ignore

    return akshare


def _as_float(value: Any) -> float | None:
    if value in (None, "", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _previous_close(
    *,
    close: float | None,
    change_amount: float | None,
) -> float | None:
    if close is None or change_amount is None:
        return None
    return round(close - change_amount, 4)
