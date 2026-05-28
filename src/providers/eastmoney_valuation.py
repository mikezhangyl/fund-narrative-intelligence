from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.errors import ProviderContractError
from src.providers.security_market import eastmoney_a_share_secid
from src.validation import validate_valuation_snapshot_payload

EASTMONEY_VALUATION_URL = "https://push2.eastmoney.com/api/qt/stock/get"
EASTMONEY_VALUATION_PROVIDER = "eastmoney-valuation"
EASTMONEY_VALUATION_VERSION = "eastmoney-valuation-v1"


class EastmoneyValuationProvider:
    provider_name = EASTMONEY_VALUATION_PROVIDER
    provider_version = EASTMONEY_VALUATION_VERSION
    source_url = EASTMONEY_VALUATION_URL

    def __init__(self, fetcher: Callable[[str], dict[str, Any]] | None = None):
        self.fetcher = fetcher or _fetch_json
        self.degradation_events: list[dict[str, str]] = []

    def get_valuation_snapshots(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payloads = []
        failed_stock_codes = []
        for stock_code in stock_codes:
            if _eastmoney_secid(stock_code) is None:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unsupported_market",
                        "provider": self.provider_name,
                        "reason": (
                            "Eastmoney valuation currently supports A-share stock codes only: "
                            f"{stock_code}"
                        ),
                    }
                )
                continue
            url = build_eastmoney_valuation_url(stock_code)
            try:
                response = _fetch_with_retry(self.fetcher, url)
                payloads.append(
                    normalize_eastmoney_valuation_response(
                        response=response,
                        requested_stock_codes=[stock_code],
                        source_url=url,
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
                            f"Eastmoney valuation fetch failed for {stock_code}: {exc}"
                        ),
                    }
                )

        valuations = [
            valuation for payload in payloads for valuation in payload["valuations"]
        ]
        payload_missing_codes = [
            code for payload in payloads for code in payload["missing_stock_codes"]
        ]
        missing_stock_codes = sorted(set([*failed_stock_codes, *payload_missing_codes]))
        payload = {
            "version": "valuation-snapshot-v1",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(
                valuations=valuations,
                missing_stock_codes=missing_stock_codes,
            ),
            "source_url": _combined_source_url(payloads),
            "retrieved_at": retrieved_at,
            "valuation_basis": "provider_valuation_metrics",
            "valuations": valuations,
            "missing_stock_codes": missing_stock_codes,
        }
        validate_valuation_snapshot_payload(payload)
        return payload


def build_eastmoney_valuation_url(stock_code: str) -> str:
    secid = _eastmoney_secid(stock_code)
    if secid is None:
        raise ProviderContractError(
            f"Eastmoney valuation does not support stock code: {stock_code}"
        )
    params = {
        "secid": secid,
        "fields": ",".join(
            [
                "f43",
                "f57",
                "f58",
                "f60",
                "f116",
                "f117",
                "f162",
                "f167",
                "f168",
                "f170",
            ]
        ),
    }
    return f"{EASTMONEY_VALUATION_URL}?{urlencode(params)}"


def normalize_eastmoney_valuation_response(
    response: dict[str, Any],
    requested_stock_codes: list[str],
    source_url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict):
        raise ProviderContractError("Eastmoney valuation response missing data")

    stock_code = str(data.get("f57") or "").strip()
    stock_name = str(data.get("f58") or "").strip()
    if not stock_code:
        raise ProviderContractError("Eastmoney valuation response missing stock code")
    latest_price = _scaled_float(data.get("f43"))
    previous_close = _scaled_float(data.get("f60"))
    pe_ttm = _scaled_float(data.get("f162"))
    pb = _scaled_float(data.get("f167"))
    valuation = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "latest_price": latest_price,
        "previous_close": previous_close,
        "price_change_percent": _scaled_float(data.get("f170")),
        "valuation_pressure": _valuation_pressure(pe_ttm=pe_ttm, pb=pb),
        "source": "provider_valuation_metrics",
        "source_provider": EASTMONEY_VALUATION_PROVIDER,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "market_cap": _optional_float(data.get("f116")),
        "float_market_cap": _optional_float(data.get("f117")),
        "turnover_rate": _scaled_float(data.get("f168")),
    }
    requested_codes = {str(code) for code in requested_stock_codes}
    missing_stock_codes = sorted(requested_codes - {stock_code})
    payload = {
        "version": "valuation-snapshot-v1",
        "provider_name": EASTMONEY_VALUATION_PROVIDER,
        "provider_version": EASTMONEY_VALUATION_VERSION,
        "data_quality": "fresh" if not missing_stock_codes else "partial",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "valuation_basis": "provider_valuation_metrics",
        "valuations": [valuation],
        "missing_stock_codes": missing_stock_codes,
    }
    validate_valuation_snapshot_payload(payload)
    return payload


def _valuation_pressure(pe_ttm: float | None, pb: float | None) -> str:
    if pe_ttm is None and pb is None:
        return "unknown"
    if (pe_ttm is not None and pe_ttm >= 40) or (pb is not None and pb >= 8):
        return "elevated"
    if (pe_ttm is not None and 0 < pe_ttm <= 12) or (pb is not None and 0 < pb <= 1.5):
        return "discounted"
    return "neutral"


def _data_quality(
    valuations: list[dict[str, Any]],
    missing_stock_codes: list[str],
) -> str:
    if not valuations:
        return "unavailable"
    if missing_stock_codes:
        return "partial"
    return "fresh"


def _combined_source_url(payloads: list[dict[str, Any]]) -> str:
    source_urls = {payload["source_url"] for payload in payloads}
    if len(source_urls) == 1:
        return source_urls.pop()
    if source_urls:
        return "multiple://valuation"
    return EASTMONEY_VALUATION_URL


def _eastmoney_secid(stock_code: str) -> str:
    return eastmoney_a_share_secid(stock_code)


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
            if attempt + 1 < attempts:
                time.sleep(0.2)
    if last_error is None:
        raise ProviderContractError("Eastmoney valuation fetch failed")
    raise last_error


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ProviderContractError("Eastmoney valuation response must be an object")
    return payload


def _scaled_float(value: Any) -> float | None:
    parsed = _optional_float(value)
    if parsed is None:
        return None
    return round(parsed / 100, 4)


def _optional_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
