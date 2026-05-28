from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.market_data.providers.local_gateway import LocalGatewayMarketDataProvider
from src.providers.mock import MockDataProvider
from src.providers.provenance import (
    PROVIDER_LAYERS,
    build_provider_foundation,
    layer_from_provider_metadata,
    mock_layer,
)
from src.validation import validate_fund_payload

LOCAL_GATEWAY_FUND_PROVIDER = "local-gateway-fund-holdings"
LOCAL_GATEWAY_FUND_VERSION = "local-gateway-fund-holdings-v1"


class LocalGatewayFundHoldingProvider:
    provider_name = LOCAL_GATEWAY_FUND_PROVIDER
    provider_version = LOCAL_GATEWAY_FUND_VERSION

    def __init__(
        self,
        *,
        gateway_provider: Any | None = None,
        fallback_provider: MockDataProvider | None = None,
    ):
        self.gateway_provider = (
            gateway_provider
            if gateway_provider is not None
            else LocalGatewayMarketDataProvider.from_env()
        )
        self.fallback_provider = fallback_provider or MockDataProvider()
        self.degradation_events: list[dict[str, str]] = []

    def get_fund_holdings(self, fund_code: str) -> dict[str, Any]:
        if self.gateway_provider is None:
            self._record_fallback("MARKET_DATA_GATEWAY_URL is not configured")
            return self.fallback_provider.get_fund_holdings(fund_code)
        try:
            payload = _build_gateway_fund_payload(
                fund_code=fund_code,
                profile_rows=self.gateway_provider.fetch_fund_profile(fund_code=fund_code),
                holding_rows=self.gateway_provider.fetch_fund_holdings(
                    fund_code=fund_code,
                    limit=10,
                ),
            )
            validate_fund_payload(payload, fund_code=fund_code)
            return payload
        except Exception as exc:
            self._record_fallback(f"Local gateway fund holdings fetch failed: {exc}")
            return self.fallback_provider.get_fund_holdings(fund_code)

    def get_narrative_registry(self) -> dict[str, Any]:
        return self.fallback_provider.get_narrative_registry()

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        return self.fallback_provider.get_stock_narrative_mappings()

    def get_mapping_exclusions(self) -> dict[str, Any]:
        return self.fallback_provider.get_mapping_exclusions()

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
            note=(
                "Fund profile and holdings fetched through the local gateway when "
                "available; falls back to V1 mock fixtures on gateway failure."
            ),
        )
        return build_provider_foundation(
            layers=layers,
            degradation_events=degradation_events,
        )

    def _record_fallback(self, reason: str) -> None:
        self.degradation_events.append(
            {
                "type": "provider_fallback",
                "requested_provider_mode": "gateway",
                "fallback_provider_mode": "mock",
                "reason": reason,
            }
        )


def _build_gateway_fund_payload(
    *,
    fund_code: str,
    profile_rows: list[dict[str, Any]],
    holding_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not holding_rows:
        raise ValueError("gateway fund holdings returned no rows")
    profile = profile_rows[0] if profile_rows else {}
    as_of_date = _as_of_date(holding_rows, profile)
    retrieved_at = str(
        profile.get("retrieved_at")
        or holding_rows[0].get("retrieved_at")
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    source_url = holding_rows[0].get("source_url") or profile.get("source_url")
    payload = {
        "as_of_date": as_of_date,
        "fund": {
            "fund_code": fund_code,
            "fund_name": str(profile.get("fund_name") or f"Gateway Fund {fund_code}"),
            "fund_type": str(profile.get("fund_type") or "fund"),
            "currency": str(profile.get("currency") or "CNY"),
            "provider_metadata": {
                "provider_name": LOCAL_GATEWAY_FUND_PROVIDER,
                "provider_version": LOCAL_GATEWAY_FUND_VERSION,
                "source_url": source_url,
                "as_of_date": as_of_date,
                "retrieved_at": retrieved_at,
                "data_quality": str(profile.get("data_quality") or "fresh"),
                "confidence_multiplier": 0.9,
            },
        },
        "holdings": [_holding_payload(row) for row in holding_rows[:10]],
    }
    return payload


def _as_of_date(
    holding_rows: list[dict[str, Any]],
    profile: dict[str, Any],
) -> str:
    return str(
        holding_rows[0].get("as_of_date")
        or holding_rows[0].get("trade_date")
        or profile.get("as_of_date")
        or ""
    )


def _holding_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stock_code": str(row.get("stock_code") or row.get("symbol") or "").strip(),
        "stock_name": str(row.get("stock_name") or row.get("name") or "").strip(),
        "weight": float(row.get("weight")),
        "holding_change": _optional_float(row.get("holding_change"), default=0.0),
        "industry": row.get("industry"),
    }
    return {key: value for key, value in payload.items() if value is not None}


def _optional_float(value: Any, *, default: float) -> float:
    if value in (None, ""):
        return default
    return float(value)
