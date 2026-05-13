from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.errors import ProviderContractError, ProviderFetchError
from src.providers.mock import MockDataProvider
from src.providers.provenance import (
    PROVIDER_LAYERS,
    build_provider_foundation,
    layer_from_provider_metadata,
    mock_layer,
)
from src.validation import validate_fund_payload

EASTMONEY_HOLDINGS_URL = "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition"
EASTMONEY_PARAMS = {
    "appType": "ttjj",
    "deviceid": "3EA024C2-7F22-408B-95E4-383D38160FB3",
    "plat": "Iphone",
    "product": "EFund",
    "serverVersion": "6.2.8",
    "version": "6.2.8",
}


class EastmoneyFundHoldingProvider:
    """Eastmoney/Tiantian fund-holdings adapter with local fixture fallback."""

    provider_name = "eastmoney-fundmobapi"
    provider_version = "eastmoney-v1"

    def __init__(
        self,
        fallback_provider: MockDataProvider | None = None,
        fetcher: Callable[[str], dict[str, Any]] | None = None,
    ):
        self.fallback_provider = fallback_provider or MockDataProvider()
        self.fetcher = fetcher or _fetch_json
        self.degradation_events: list[dict[str, str]] = []

    def get_fund_holdings(self, fund_code: str) -> dict[str, Any]:
        source_url = build_eastmoney_holdings_url(fund_code)
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        try:
            response = self.fetcher(source_url)
            payload = normalize_eastmoney_holdings_response(
                response=response,
                fund_code=fund_code,
                source_url=source_url,
                retrieved_at=retrieved_at,
            )
            validate_fund_payload(payload, fund_code=fund_code)
            return payload
        except Exception as exc:
            self.degradation_events.append(
                {
                    "type": "provider_fallback",
                    "requested_provider_mode": "eastmoney",
                    "fallback_provider_mode": "mock",
                    "reason": f"Eastmoney holdings fetch failed: {exc}",
                }
            )
            return self.fallback_provider.get_fund_holdings(fund_code)

    def get_narrative_registry(self) -> dict[str, Any]:
        return self.fallback_provider.get_narrative_registry()

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_stock_narrative_mappings()

    def get_evidence(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_evidence()

    def get_signal_events(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_signal_events()

    def get_provider_foundation(
        self,
        fund_provider_metadata: dict[str, Any],
        degradation_events: list[dict[str, str]],
    ) -> dict[str, Any]:
        layers = {layer: mock_layer(layer) for layer in PROVIDER_LAYERS}
        layers["holdings"] = layer_from_provider_metadata(
            layer="holdings",
            provider_metadata=fund_provider_metadata,
            note="Fund holdings fetched from Eastmoney when available; falls back to V1 mock fixtures on provider failure.",
        )
        return build_provider_foundation(
            layers=layers,
            degradation_events=degradation_events,
        )


def build_eastmoney_holdings_url(fund_code: str) -> str:
    params = {"FCODE": fund_code, **EASTMONEY_PARAMS}
    return f"{EASTMONEY_HOLDINGS_URL}?{urlencode(params)}"


def normalize_eastmoney_holdings_response(
    response: dict[str, Any],
    fund_code: str,
    source_url: str,
    retrieved_at: str,
) -> dict[str, Any]:
    stocks = _extract_fund_stocks(response)
    as_of_date = response.get("Expansion")
    if not as_of_date:
        raise ProviderContractError("Eastmoney response missing Expansion date")

    holdings = []
    for stock in stocks[:10]:
        weight = _parse_percent(stock.get("JZBL"), field_name="JZBL")
        holdings.append(
            {
                "stock_code": str(stock.get("GPDM", "")).strip(),
                "stock_name": str(stock.get("GPJC", "")).strip(),
                "weight": weight,
                "holding_change": _parse_percent(
                    stock.get("PCTNVCHG"), field_name="PCTNVCHG", default=0
                ),
                "industry": stock.get("INDEXNAME") or None,
            }
        )

    if not holdings:
        raise ProviderContractError("Eastmoney response contained no fund stocks")

    return {
        "as_of_date": as_of_date,
        "fund": {
            "fund_code": fund_code,
            "fund_name": f"Eastmoney Fund {fund_code}",
            "fund_type": "fund",
            "currency": "CNY",
            "provider_metadata": {
                "provider_name": "eastmoney-fundmobapi",
                "provider_version": "eastmoney-v1",
                "source_url": source_url,
                "as_of_date": as_of_date,
                "retrieved_at": retrieved_at,
                "data_quality": "fresh",
                "confidence_multiplier": 0.9,
            },
        },
        "holdings": holdings,
    }


def _extract_fund_stocks(response: dict[str, Any]) -> list[dict[str, Any]]:
    datas = response.get("Datas")
    if isinstance(datas, dict):
        stocks = datas.get("fundStocks")
    else:
        stocks = None
    if not isinstance(stocks, list):
        raise ProviderContractError("Eastmoney response missing Datas.fundStocks")
    return stocks


def _parse_percent(
    value: Any, field_name: str, default: float | None = None
) -> float:
    if value in (None, "", "--"):
        if default is not None:
            return default
        raise ProviderContractError(f"Eastmoney field {field_name} is missing")
    try:
        return round(float(value) / 100, 6)
    except ValueError as exc:
        raise ProviderContractError(
            f"Eastmoney field {field_name} is not numeric: {value}"
        ) from exc


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://fund.eastmoney.com/",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ProviderFetchError(f"Failed to fetch Eastmoney holdings: {exc}") from exc
