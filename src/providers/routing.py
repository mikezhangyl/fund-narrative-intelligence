from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from src.providers.akshare_market import AkshareMarketDataProvider
from src.providers.cninfo import CNInfoAnnouncementProvider
from src.providers.eastmoney_financials import EastmoneyFinancialMetricsProvider
from src.providers.eastmoney_market import EastmoneyMarketDataProvider
from src.providers.eastmoney_valuation import EastmoneyValuationProvider
from src.providers.factory import select_data_provider
from src.providers.intelligence import (
    MockAnnouncementProvider,
    MockMarketDataProvider,
    MockNewsEvidenceProvider,
    MockValuationProvider,
)
from src.providers.local_gateway_fund import LocalGatewayFundHoldingProvider
from src.providers.news import (
    GoogleNewsRssEvidenceProvider,
    MultiSourceNewsEvidenceProvider,
    SinaFinanceRollNewsProvider,
    StcnFinanceNewsProvider,
)
from src.providers.tushare_financials import TushareFinancialMetricsProvider
from src.providers.tushare_holdings import TushareFundHoldingProvider
from src.providers.tushare_market import TushareMarketDataProvider
from src.providers.tushare_valuation import TushareValuationProvider

ROUTABLE_PROVIDER_LAYERS = (
    "holdings",
    "market_quotes",
    "valuation_snapshots",
    "financial_metrics",
    "announcements",
    "news_evidence",
)

DEFAULT_LAYER_PRIMARY_PROVIDERS = {
    "market_quotes": "eastmoney",
    "valuation_snapshots": "eastmoney",
    "financial_metrics": "eastmoney",
    "announcements": "cninfo",
    "news_evidence": "multi-source-news",
}

ProviderFactory = Callable[[], Any]


@dataclass(frozen=True)
class LayerProviderRoute:
    primary: str
    fallback: str | None = None


@dataclass(frozen=True)
class RoutedProviderCandidate:
    provider: Any
    degradation_events: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedLayerProviderSelection:
    layer: str
    primary_name: str
    primary_provider: Any
    primary_degradation_events: list[dict[str, str]] = field(default_factory=list)
    fallback_name: str | None = None
    fallback_provider: Any | None = None
    fallback_degradation_events: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderRoutingConfig:
    routes: dict[str, LayerProviderRoute] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any] | "ProviderRoutingConfig" | None,
    ) -> "ProviderRoutingConfig":
        if payload is None:
            return cls()
        if isinstance(payload, ProviderRoutingConfig):
            return payload
        if not isinstance(payload, Mapping):
            raise ValueError("provider_routing must be a mapping of layer routes")

        routes: dict[str, LayerProviderRoute] = {}
        for layer, route_payload in payload.items():
            if layer not in ROUTABLE_PROVIDER_LAYERS:
                raise ValueError(f"Unsupported provider routing layer: {layer}")
            if not isinstance(route_payload, Mapping):
                raise ValueError(f"provider_routing[{layer}] must be an object")
            primary = route_payload.get("primary")
            fallback = route_payload.get("fallback")
            if not isinstance(primary, str) or not primary.strip():
                raise ValueError(f"provider_routing[{layer}].primary must be a non-empty string")
            if fallback is not None and (
                not isinstance(fallback, str) or not fallback.strip()
            ):
                raise ValueError(
                    f"provider_routing[{layer}].fallback must be a non-empty string when provided"
                )
            routes[layer] = LayerProviderRoute(
                primary=primary.strip(),
                fallback=fallback.strip() if isinstance(fallback, str) else None,
            )
        return cls(routes=routes)

    def route_for(self, layer: str) -> LayerProviderRoute | None:
        return self.routes.get(layer)

    def routes_as_dict(self) -> dict[str, dict[str, str]]:
        payload: dict[str, dict[str, str]] = {}
        for layer, route in self.routes.items():
            route_payload = {"primary": route.primary}
            if route.fallback is not None:
                route_payload["fallback"] = route.fallback
            payload[layer] = route_payload
        return payload


class ProviderRouter:
    def __init__(
        self,
        provider_routing: Mapping[str, Any] | ProviderRoutingConfig | None = None,
        provider_factory_overrides: Mapping[str, Mapping[str, ProviderFactory]] | None = None,
    ):
        self.provider_routing = ProviderRoutingConfig.from_dict(provider_routing)
        self.provider_factories = _merge_provider_factories(
            base=_default_provider_factories(),
            overrides=provider_factory_overrides or {},
        )

    def resolve(
        self,
        layer: str,
        default_primary: str,
        explicit_provider: Any | None = None,
    ) -> ResolvedLayerProviderSelection:
        if layer not in ROUTABLE_PROVIDER_LAYERS:
            raise ValueError(f"Unsupported provider routing layer: {layer}")
        if explicit_provider is not None:
            explicit_name = str(
                getattr(explicit_provider, "provider_name", default_primary)
            )
            return ResolvedLayerProviderSelection(
                layer=layer,
                primary_name=explicit_name,
                primary_provider=explicit_provider,
            )

        route = self.provider_routing.route_for(layer)
        primary_name = route.primary if route is not None else default_primary
        fallback_name = route.fallback if route is not None else None

        primary_candidate = self._build_candidate(layer=layer, provider_name=primary_name)
        fallback_candidate = (
            self._build_candidate(layer=layer, provider_name=fallback_name)
            if fallback_name is not None
            else None
        )
        return ResolvedLayerProviderSelection(
            layer=layer,
            primary_name=primary_name,
            primary_provider=primary_candidate.provider,
            primary_degradation_events=list(primary_candidate.degradation_events),
            fallback_name=fallback_name,
            fallback_provider=(
                fallback_candidate.provider if fallback_candidate is not None else None
            ),
            fallback_degradation_events=(
                list(fallback_candidate.degradation_events)
                if fallback_candidate is not None
                else []
            ),
        )

    def default_primary_for(self, layer: str) -> str:
        if layer == "holdings":
            raise ValueError("holdings default primary depends on provider_mode")
        return DEFAULT_LAYER_PRIMARY_PROVIDERS[layer]

    def _build_candidate(
        self,
        layer: str,
        provider_name: str | None,
    ) -> RoutedProviderCandidate:
        if provider_name is None:
            raise ValueError(f"provider_name is required for routed layer {layer}")
        factories = self.provider_factories.get(layer)
        if factories is None or provider_name not in factories:
            raise ValueError(
                f"Unsupported provider '{provider_name}' for routed layer '{layer}'"
            )
        candidate = factories[provider_name]()
        if isinstance(candidate, RoutedProviderCandidate):
            return candidate
        return RoutedProviderCandidate(provider=candidate)


def _default_provider_factories() -> dict[str, dict[str, ProviderFactory]]:
    return {
        "holdings": {
            "mock": lambda: _provider_selection_candidate("mock"),
            "real": lambda: _provider_selection_candidate("real"),
            "eastmoney": lambda: _provider_selection_candidate("eastmoney"),
            "tushare": lambda: TushareFundHoldingProvider(),
            "gateway": lambda: LocalGatewayFundHoldingProvider(),
        },
        "market_quotes": {
            "mock": lambda: MockMarketDataProvider(),
            "akshare": lambda: AkshareMarketDataProvider(),
            "tushare": lambda: TushareMarketDataProvider(),
            "eastmoney": lambda: EastmoneyMarketDataProvider(),
        },
        "valuation_snapshots": {
            "mock": lambda: MockValuationProvider(),
            "tushare": lambda: TushareValuationProvider(),
            "eastmoney": lambda: EastmoneyValuationProvider(),
        },
        "financial_metrics": {
            "tushare": lambda: TushareFinancialMetricsProvider(),
            "eastmoney": lambda: EastmoneyFinancialMetricsProvider(),
        },
        "announcements": {
            "mock": lambda: MockAnnouncementProvider(),
            "cninfo": lambda: CNInfoAnnouncementProvider(),
        },
        "news_evidence": {
            "mock": lambda: MockNewsEvidenceProvider(),
            "google-news-rss": lambda: GoogleNewsRssEvidenceProvider(),
            "sina-finance-roll": lambda: SinaFinanceRollNewsProvider(),
            "stcn-finance": lambda: StcnFinanceNewsProvider(),
            "multi-source-news": lambda: MultiSourceNewsEvidenceProvider(),
        },
    }


def _provider_selection_candidate(provider_mode: str) -> RoutedProviderCandidate:
    selection = select_data_provider(provider_mode)
    return RoutedProviderCandidate(
        provider=selection.provider,
        degradation_events=list(selection.degradation_events),
    )


def _merge_provider_factories(
    base: dict[str, dict[str, ProviderFactory]],
    overrides: Mapping[str, Mapping[str, ProviderFactory]],
) -> dict[str, dict[str, ProviderFactory]]:
    merged = {layer: dict(factories) for layer, factories in base.items()}
    for layer, providers in overrides.items():
        if layer not in ROUTABLE_PROVIDER_LAYERS:
            raise ValueError(f"Unsupported provider routing layer: {layer}")
        merged[layer] = {
            **merged.get(layer, {}),
            **dict(providers),
        }
    return merged
