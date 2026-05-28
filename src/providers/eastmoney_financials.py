from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.errors import ProviderContractError
from src.providers.security_market import eastmoney_a_share_secucode
from src.validation import validate_financial_metrics_payload

EASTMONEY_FINANCIAL_METRICS_URL = (
    "https://datacenter.eastmoney.com/securities/api/data/get"
)
EASTMONEY_FINANCIAL_METRICS_PROVIDER = "eastmoney-financial-metrics"
EASTMONEY_FINANCIAL_METRICS_VERSION = "eastmoney-financial-metrics-v1"


class EastmoneyFinancialMetricsProvider:
    provider_name = EASTMONEY_FINANCIAL_METRICS_PROVIDER
    provider_version = EASTMONEY_FINANCIAL_METRICS_VERSION
    source_url = EASTMONEY_FINANCIAL_METRICS_URL

    def __init__(self, fetcher: Callable[[str], dict[str, Any]] | None = None):
        self.fetcher = fetcher or _fetch_json
        self.degradation_events: list[dict[str, str]] = []

    def get_financial_metrics(self, stock_codes: list[str]) -> dict[str, Any]:
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payloads = []
        failed_stock_codes = []
        for stock_code in stock_codes:
            if _eastmoney_secucode(stock_code) is None:
                failed_stock_codes.append(str(stock_code))
                self.degradation_events.append(
                    {
                        "type": "provider_unsupported_market",
                        "provider": self.provider_name,
                        "reason": (
                            "Eastmoney financial metrics currently support A-share stock codes only: "
                            f"{stock_code}"
                        ),
                    }
                )
                continue
            url = build_eastmoney_financial_metrics_url(stock_code)
            try:
                response = _fetch_with_retry(self.fetcher, url)
                payloads.append(
                    normalize_eastmoney_financial_metrics_response(
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
                            "Eastmoney financial metrics fetch failed for "
                            f"{stock_code}: {exc}"
                        ),
                    }
                )

        metrics = [metric for payload in payloads for metric in payload["metrics"]]
        payload_missing_codes = [
            code for payload in payloads for code in payload["missing_stock_codes"]
        ]
        missing_stock_codes = sorted(set([*failed_stock_codes, *payload_missing_codes]))
        payload = {
            "version": "financial-metrics-v1",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": _data_quality(metrics, missing_stock_codes),
            "source_url": _combined_source_url(payloads),
            "retrieved_at": retrieved_at,
            "metrics": metrics,
            "missing_stock_codes": missing_stock_codes,
        }
        validate_financial_metrics_payload(payload)
        return payload


def build_eastmoney_financial_metrics_url(stock_code: str) -> str:
    secucode = _eastmoney_secucode(stock_code)
    if secucode is None:
        raise ProviderContractError(
            f"Eastmoney financial metrics do not support stock code: {stock_code}"
        )
    params = {
        "type": "RPT_F10_FINANCE_MAINFINADATA",
        "sty": "APP_F10_MAINFINADATA",
        "filter": f'(SECUCODE="{secucode}")',
        "p": "1",
        "ps": "1",
        "sr": "-1",
        "st": "REPORT_DATE",
        "source": "HSF10",
        "client": "PC",
    }
    return f"{EASTMONEY_FINANCIAL_METRICS_URL}?{urlencode(params)}"


def normalize_eastmoney_financial_metrics_response(
    response: dict[str, Any],
    requested_stock_codes: list[str],
    source_url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    result = response.get("result") if isinstance(response, dict) else None
    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, list) or not data:
        raise ProviderContractError("Eastmoney financial metrics response missing data")
    row = data[0]
    if not isinstance(row, dict):
        raise ProviderContractError("Eastmoney financial metrics row must be an object")

    stock_code = str(row.get("SECURITY_CODE") or "").strip()
    stock_name = str(row.get("SECURITY_NAME_ABBR") or "").strip()
    if not stock_code:
        raise ProviderContractError("Eastmoney financial metrics missing stock code")
    metric = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "report_date": _date_only(row.get("REPORT_DATE")),
        "report_type": str(row.get("REPORT_TYPE") or ""),
        "notice_date": _date_only(row.get("NOTICE_DATE")),
        "currency": str(row.get("CURRENCY") or ""),
        "revenue": _optional_float(row.get("TOTALOPERATEREVE")),
        "revenue_yoy": _optional_float(row.get("TOTALOPERATEREVETZ")),
        "parent_net_profit": _optional_float(row.get("PARENTNETPROFIT")),
        "parent_net_profit_yoy": _optional_float(row.get("PARENTNETPROFITTZ")),
        "deduct_parent_net_profit_yoy": _optional_float(row.get("KCFJCXSYJLRTZ")),
        "roe": _optional_float(row.get("ROEJQ")),
        "gross_margin": _optional_float(row.get("XSMLL")),
        "net_margin": _optional_float(row.get("XSJLL")),
        "debt_asset_ratio": _optional_float(row.get("ZCFZL")),
        "source": "provider_financial_metrics",
        "source_provider": EASTMONEY_FINANCIAL_METRICS_PROVIDER,
        "source_url": source_url,
        "retrieved_at": retrieved_at,
    }
    requested_codes = {str(code) for code in requested_stock_codes}
    missing_stock_codes = sorted(requested_codes - {stock_code})
    payload = {
        "version": "financial-metrics-v1",
        "provider_name": EASTMONEY_FINANCIAL_METRICS_PROVIDER,
        "provider_version": EASTMONEY_FINANCIAL_METRICS_VERSION,
        "data_quality": "fresh" if not missing_stock_codes else "partial",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "metrics": [metric],
        "missing_stock_codes": missing_stock_codes,
    }
    validate_financial_metrics_payload(payload)
    return payload


def _data_quality(
    metrics: list[dict[str, Any]],
    missing_stock_codes: list[str],
) -> str:
    if not metrics:
        return "unavailable"
    if missing_stock_codes:
        return "partial"
    return "fresh"


def _combined_source_url(payloads: list[dict[str, Any]]) -> str:
    source_urls = {payload["source_url"] for payload in payloads}
    if len(source_urls) == 1:
        return source_urls.pop()
    if source_urls:
        return "multiple://financial-metrics"
    return EASTMONEY_FINANCIAL_METRICS_URL


def _eastmoney_secucode(stock_code: str) -> str:
    return eastmoney_a_share_secucode(stock_code)


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
        raise ProviderContractError("Eastmoney financial metrics fetch failed")
    raise last_error


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://emweb.securities.eastmoney.com/",
        },
    )
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ProviderContractError(
            "Eastmoney financial metrics response must be an object"
        )
    return payload


def _date_only(value: Any) -> str:
    text = str(value or "")
    if len(text) >= 10:
        return text[:10]
    return text


def _optional_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
