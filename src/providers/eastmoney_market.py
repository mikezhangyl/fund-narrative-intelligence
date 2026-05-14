from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.errors import ProviderContractError, ProviderFetchError
from src.validation import validate_market_quote_payload

EASTMONEY_MARKET_QUOTE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
YAHOO_MARKET_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


class EastmoneyMarketDataProvider:
    provider_name = "eastmoney-market-quote"
    provider_version = "eastmoney-market-quote-v1"
    source_url = EASTMONEY_MARKET_QUOTE_URL

    def __init__(
        self,
        fetcher: Callable[[str], dict[str, Any]] | None = None,
        yahoo_fetcher: Callable[[str], dict[str, Any]] | None = None,
    ):
        self.fetcher = fetcher or _fetch_json
        self.yahoo_fetcher = yahoo_fetcher or _fetch_json
        self.degradation_events: list[dict[str, str]] = []

    def get_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        quote_payloads = []
        failed_stock_codes = []

        for stock_code in stock_codes:
            try:
                quote_payloads.append(
                    self._get_single_stock_quote_payload(
                        stock_code=stock_code,
                        retrieved_at=retrieved_at,
                    )
                )
            except Exception as exc:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider": self.provider_name,
                        "reason": (
                            f"Eastmoney quote fetch failed for {stock_code}: {exc}"
                        ),
                    }
                )

        quotes = [quote for payload in quote_payloads for quote in payload["quotes"]]
        payload_missing_codes = [
            code
            for payload in quote_payloads
            for code in payload["missing_stock_codes"]
        ]
        missing_stock_codes = sorted(set([*failed_stock_codes, *payload_missing_codes]))
        payload = {
            "version": self.provider_version,
            "provider_name": _combined_provider_name(quote_payloads),
            "provider_version": self.provider_version,
            "data_quality": _data_quality(quotes=quotes, missing_stock_codes=missing_stock_codes),
            "source_url": _combined_source_url(quote_payloads),
            "retrieved_at": retrieved_at,
            "quotes": quotes,
            "missing_stock_codes": missing_stock_codes,
        }
        validate_market_quote_payload(payload)
        return payload

    def _get_single_stock_quote_payload(
        self,
        stock_code: str,
        retrieved_at: str,
    ) -> dict[str, Any]:
        quote_url = build_eastmoney_quote_url(stock_code)
        try:
            response = _fetch_with_retry(self.fetcher, quote_url)
            return normalize_eastmoney_quote_response(
                response=response,
                requested_stock_codes=[stock_code],
                source_url=quote_url,
                retrieved_at=retrieved_at,
            )
        except Exception as exc:
            self.degradation_events.append(
                {
                    "type": "provider_fallback",
                    "provider": self.provider_name,
                    "fallback_provider": "yahoo-chart",
                    "reason": f"Eastmoney quote fetch failed for {stock_code}: {exc}",
                }
            )
            yahoo_url = build_yahoo_quote_url(stock_code)
            response = _fetch_with_retry(self.yahoo_fetcher, yahoo_url)
            return normalize_yahoo_quote_response(
                response=response,
                requested_stock_codes=[stock_code],
                source_url=yahoo_url,
                retrieved_at=retrieved_at,
            )


def build_eastmoney_quote_url(stock_code: str) -> str:
    params = {
        "secid": _eastmoney_secid(stock_code),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": "0",
        "end": "20500101",
    }
    return f"{EASTMONEY_MARKET_QUOTE_URL}?{urlencode(params)}"


def build_yahoo_quote_url(stock_code: str) -> str:
    return f"{YAHOO_MARKET_QUOTE_URL}/{_yahoo_symbol(stock_code)}?range=5d&interval=1d"


def normalize_eastmoney_quote_response(
    response: dict[str, Any],
    requested_stock_codes: list[str],
    source_url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        raise ProviderContractError("Eastmoney quote response missing data")

    klines = data.get("klines")
    if not isinstance(klines, list) or not klines:
        raise ProviderContractError("Eastmoney quote response missing data.klines")

    latest = str(klines[-1]).split(",")
    if len(latest) < 10:
        raise ProviderContractError("Eastmoney quote kline row is incomplete")

    stock_code = str(data.get("code") or "").strip()
    stock_name = str(data.get("name") or "").strip()
    close = _parse_optional_float(latest[2])
    change_amount = _parse_optional_float(latest[9])
    quote = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "source_provider": "eastmoney",
        "source_url": source_url,
        "latest_price": close,
        "change_percent": _parse_optional_float(latest[8]),
        "change_amount": change_amount,
        "volume": _parse_optional_float(latest[5]),
        "amount": _parse_optional_float(latest[6]),
        "high": _parse_optional_float(latest[3]),
        "low": _parse_optional_float(latest[4]),
        "open": _parse_optional_float(latest[1]),
        "previous_close": _previous_close(close=close, change_amount=change_amount),
        "retrieved_at": retrieved_at,
    }
    requested_codes = {str(code) for code in requested_stock_codes}
    missing_stock_codes = sorted(requested_codes - {stock_code})
    payload = {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "eastmoney-market-quote",
        "provider_version": "eastmoney-market-quote-v1",
        "data_quality": "fresh" if not missing_stock_codes else "partial",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "quotes": [quote],
        "missing_stock_codes": missing_stock_codes,
    }
    validate_market_quote_payload(payload)
    return payload


def normalize_yahoo_quote_response(
    response: dict[str, Any],
    requested_stock_codes: list[str],
    source_url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    result = _yahoo_result(response)
    meta = result.get("meta", {})
    quote_data = result.get("indicators", {}).get("quote", [{}])[0]
    closes = quote_data.get("close") or []
    opens = quote_data.get("open") or []
    highs = quote_data.get("high") or []
    lows = quote_data.get("low") or []
    volumes = quote_data.get("volume") or []
    latest_index = _latest_non_null_index(closes)
    if latest_index is None:
        raise ProviderContractError("Yahoo chart response contained no close prices")

    stock_code = _stock_code_from_yahoo_symbol(str(meta.get("symbol") or ""))
    close = _parse_optional_float(closes[latest_index])
    previous_close = _parse_optional_float(meta.get("chartPreviousClose"))
    change_amount = _change_amount(close=close, previous_close=previous_close)
    quote = {
        "stock_code": stock_code,
        "stock_name": str(meta.get("shortName") or meta.get("symbol") or stock_code),
        "source_provider": "yahoo-chart",
        "source_url": source_url,
        "latest_price": close,
        "change_percent": _change_percent(
            close=close,
            previous_close=previous_close,
        ),
        "change_amount": change_amount,
        "volume": _list_value(volumes, latest_index),
        "amount": None,
        "high": _list_value(highs, latest_index),
        "low": _list_value(lows, latest_index),
        "open": _list_value(opens, latest_index),
        "previous_close": previous_close,
        "retrieved_at": retrieved_at,
    }
    requested_codes = {str(code) for code in requested_stock_codes}
    missing_stock_codes = sorted(requested_codes - {stock_code})
    payload = {
        "version": "eastmoney-market-quote-v1",
        "provider_name": "yahoo-chart",
        "provider_version": "yahoo-chart-v1",
        "data_quality": "fresh" if not missing_stock_codes else "partial",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "quotes": [quote],
        "missing_stock_codes": missing_stock_codes,
    }
    validate_market_quote_payload(payload)
    return payload


def _yahoo_result(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("chart", {}).get("result") if isinstance(response, dict) else None
    if not isinstance(result, list) or not result:
        raise ProviderContractError("Yahoo chart response missing chart.result")
    if not isinstance(result[0], dict):
        raise ProviderContractError("Yahoo chart result must be an object")
    return result[0]


def _data_quality(
    quotes: list[dict[str, Any]], missing_stock_codes: list[str]
) -> str:
    if not quotes:
        return "unavailable"
    if missing_stock_codes:
        return "partial"
    return "fresh"


def _combined_provider_name(quote_payloads: list[dict[str, Any]]) -> str:
    providers = {payload["provider_name"] for payload in quote_payloads}
    if len(providers) == 1:
        return providers.pop()
    if providers:
        return "mixed-market-quote"
    return EastmoneyMarketDataProvider.provider_name


def _combined_source_url(quote_payloads: list[dict[str, Any]]) -> str:
    source_urls = {payload["source_url"] for payload in quote_payloads}
    if len(source_urls) == 1:
        return source_urls.pop()
    if source_urls:
        return "multiple://market-quotes"
    return EastmoneyMarketDataProvider.source_url


def _fetch_with_retry(
    fetcher: Callable[[str], dict[str, Any]],
    url: str,
    attempts: int = 2,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return fetcher(url)
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.2)
    raise last_error or ProviderFetchError("Failed to fetch Eastmoney quotes")


def _previous_close(close: float | None, change_amount: float | None) -> float | None:
    if close is None or change_amount is None:
        return None
    return round(close - change_amount, 4)


def _change_amount(close: float | None, previous_close: float | None) -> float | None:
    if close is None or previous_close is None:
        return None
    return round(close - previous_close, 4)


def _change_percent(close: float | None, previous_close: float | None) -> float | None:
    if close is None or previous_close in (None, 0):
        return None
    return round((close - previous_close) / previous_close * 100, 4)


def _latest_non_null_index(values: list[Any]) -> int | None:
    for index in range(len(values) - 1, -1, -1):
        if values[index] is not None:
            return index
    return None


def _list_value(values: list[Any], index: int) -> float | None:
    if index >= len(values):
        return None
    return _parse_optional_float(values[index])


def _eastmoney_secid(stock_code: str) -> str:
    code = str(stock_code)
    market = "1" if code.startswith(("5", "6", "9")) else "0"
    return f"{market}.{code}"


def _yahoo_symbol(stock_code: str) -> str:
    code = str(stock_code)
    suffix = "SS" if code.startswith(("5", "6", "9")) else "SZ"
    return f"{code}.{suffix}"


def _stock_code_from_yahoo_symbol(symbol: str) -> str:
    return symbol.split(".", maxsplit=1)[0]


def _parse_optional_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ProviderContractError(
            f"Eastmoney quote field is not numeric: {value}"
        ) from exc


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ProviderFetchError(f"Failed to fetch Eastmoney quotes: {exc}") from exc
