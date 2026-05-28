from __future__ import annotations

from dataclasses import dataclass, field

from src.providers.base import DataProvider
from src.providers.eastmoney import EastmoneyFundHoldingProvider
from src.providers.local_gateway_fund import LocalGatewayFundHoldingProvider
from src.providers.mock import MockDataProvider
from src.providers.tushare_holdings import TushareFundHoldingProvider


@dataclass(frozen=True)
class ProviderSelection:
    provider: DataProvider
    degradation_events: list[dict[str, str]] = field(default_factory=list)


def select_data_provider(provider_mode: str) -> ProviderSelection:
    if provider_mode == "mock":
        return ProviderSelection(provider=MockDataProvider())

    if provider_mode == "eastmoney":
        return ProviderSelection(provider=EastmoneyFundHoldingProvider())

    if provider_mode == "tushare":
        return ProviderSelection(provider=TushareFundHoldingProvider())

    if provider_mode == "gateway":
        return ProviderSelection(provider=LocalGatewayFundHoldingProvider())

    if provider_mode == "real":
        return ProviderSelection(
            provider=MockDataProvider(),
            degradation_events=[
                {
                    "type": "provider_fallback",
                    "requested_provider_mode": "real",
                    "fallback_provider_mode": "mock",
                    "reason": "Real providers are not implemented in V1; mock provider used to keep the pipeline runnable.",
                }
            ],
        )

    raise ValueError(f"Unsupported provider mode: {provider_mode}")
