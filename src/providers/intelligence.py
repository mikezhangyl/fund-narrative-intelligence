from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.config import FIXTURE_DIR
from src.errors import FixtureNotFoundError
from src.providers.provenance import (
    MOCK_PROVIDER_NAME,
    MOCK_PROVIDER_VERSION,
    mock_layer,
)
from src.validation import (
    validate_evidence_payload,
    validate_mapping_exclusion_payload,
    validate_mapping_payload,
    validate_registry_payload,
    validate_signal_payload,
)


class NarrativeRegistryProvider(Protocol):
    def get_narrative_registry(self) -> dict[str, Any]:
        raise NotImplementedError


class StockNarrativeMappingProvider(Protocol):
    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class MappingExclusionProvider(Protocol):
    def get_mapping_exclusions(self) -> dict[str, Any]:
        raise NotImplementedError


class EvidenceProvider(Protocol):
    def get_evidence(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class SignalEventProvider(Protocol):
    def get_signal_events(self) -> list[dict[str, Any]]:
        raise NotImplementedError


class MarketDataProvider(Protocol):
    def get_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        raise NotImplementedError


class ValuationProvider(Protocol):
    def get_valuation_snapshots(self, stock_codes: list[str]) -> dict[str, Any]:
        raise NotImplementedError


class AnnouncementProvider(Protocol):
    def get_announcements(
        self,
        stock_codes: list[str],
        as_of_date: str,
        start_date: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class NewsEvidenceProvider(Protocol):
    def get_news_evidence(
        self,
        narrative_ids: list[str],
        as_of_date: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class MockNarrativeRegistryProvider:
    fixture_dir: Path = FIXTURE_DIR

    def get_narrative_registry(self) -> dict[str, Any]:
        payload = _load_fixture(self.fixture_dir, "narrative_registry.json")
        validate_registry_payload(payload)
        return deepcopy(payload)

    def get_provider_layer(self) -> dict[str, Any]:
        return _mock_fixture_layer("narrative_registry", "narrative_registry.json")


@dataclass(frozen=True)
class MockStockNarrativeMappingProvider:
    fixture_dir: Path = FIXTURE_DIR

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        payload = _load_fixture(self.fixture_dir, "stock_narrative_mappings.json")
        validate_mapping_payload(payload)
        return deepcopy(payload["mappings"])

    def get_provider_layer(self) -> dict[str, Any]:
        return _mock_fixture_layer("stock_mappings", "stock_narrative_mappings.json")


@dataclass(frozen=True)
class MockMappingExclusionProvider:
    fixture_dir: Path = FIXTURE_DIR

    def get_mapping_exclusions(self) -> dict[str, Any]:
        payload = _load_fixture(self.fixture_dir, "mapping_exclusions.json")
        validate_mapping_exclusion_payload(payload)
        return deepcopy(payload)


@dataclass(frozen=True)
class MockEvidenceProvider:
    fixture_dir: Path = FIXTURE_DIR

    def get_evidence(self) -> list[dict[str, Any]]:
        payload = _load_fixture(self.fixture_dir, "evidence.json")
        validate_evidence_payload(payload)
        return deepcopy(payload["evidence"])

    def get_provider_layer(self) -> dict[str, Any]:
        return _mock_fixture_layer("evidence", "evidence.json")


@dataclass(frozen=True)
class MockSignalEventProvider:
    fixture_dir: Path = FIXTURE_DIR

    def get_signal_events(self) -> list[dict[str, Any]]:
        payload = _load_fixture(self.fixture_dir, "signal_events.json")
        validate_signal_payload(payload)
        return deepcopy(payload["signal_events"])

    def get_provider_layer(self) -> dict[str, Any]:
        return _mock_fixture_layer("signals", "signal_events.json")


@dataclass(frozen=True)
class MockIntelligenceProviderSet:
    fixture_dir: Path = FIXTURE_DIR

    @property
    def narrative_registry_provider(self) -> MockNarrativeRegistryProvider:
        return MockNarrativeRegistryProvider(fixture_dir=self.fixture_dir)

    @property
    def stock_mapping_provider(self) -> MockStockNarrativeMappingProvider:
        return MockStockNarrativeMappingProvider(fixture_dir=self.fixture_dir)

    @property
    def evidence_provider(self) -> MockEvidenceProvider:
        return MockEvidenceProvider(fixture_dir=self.fixture_dir)

    @property
    def mapping_exclusion_provider(self) -> MockMappingExclusionProvider:
        return MockMappingExclusionProvider(fixture_dir=self.fixture_dir)

    @property
    def signal_event_provider(self) -> MockSignalEventProvider:
        return MockSignalEventProvider(fixture_dir=self.fixture_dir)

    def get_narrative_registry(self) -> dict[str, Any]:
        return self.narrative_registry_provider.get_narrative_registry()

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        return self.stock_mapping_provider.get_stock_narrative_mappings()

    def get_mapping_exclusions(self) -> dict[str, Any]:
        return self.mapping_exclusion_provider.get_mapping_exclusions()

    def get_evidence(self) -> list[dict[str, Any]]:
        return self.evidence_provider.get_evidence()

    def get_signal_events(self) -> list[dict[str, Any]]:
        return self.signal_event_provider.get_signal_events()

    def get_provider_layers(self) -> dict[str, dict[str, Any]]:
        return {
            "narrative_registry": self.narrative_registry_provider.get_provider_layer(),
            "stock_mappings": self.stock_mapping_provider.get_provider_layer(),
            "evidence": self.evidence_provider.get_provider_layer(),
            "signals": self.signal_event_provider.get_provider_layer(),
        }


class MockMarketDataProvider:
    provider_name = MOCK_PROVIDER_NAME
    provider_version = MOCK_PROVIDER_VERSION
    data_quality = "mock"

    def get_stock_quotes(self, stock_codes: list[str]) -> dict[str, Any]:
        return {
            "version": "market-data-mock-v1",
            "data_quality": self.data_quality,
            "quotes": [],
            "missing_stock_codes": sorted(set(stock_codes)),
        }


class MockValuationProvider:
    provider_name = MOCK_PROVIDER_NAME
    provider_version = MOCK_PROVIDER_VERSION
    data_quality = "mock"

    def get_valuation_snapshots(self, stock_codes: list[str]) -> dict[str, Any]:
        return {
            "version": "valuation-mock-v1",
            "data_quality": self.data_quality,
            "valuations": [],
            "missing_stock_codes": sorted(set(stock_codes)),
        }


class MockAnnouncementProvider:
    provider_name = MOCK_PROVIDER_NAME
    provider_version = MOCK_PROVIDER_VERSION
    data_quality = "mock"

    def get_announcements(
        self,
        stock_codes: list[str],
        as_of_date: str,
        start_date: str | None = None,
    ) -> dict[str, Any]:
        del as_of_date
        del start_date
        return {
            "version": "announcement-mock-v1",
            "data_quality": self.data_quality,
            "announcements": [],
            "missing_stock_codes": sorted(set(stock_codes)),
        }


class MockNewsEvidenceProvider:
    provider_name = MOCK_PROVIDER_NAME
    provider_version = MOCK_PROVIDER_VERSION
    data_quality = "mock"

    def get_news_evidence(
        self,
        narrative_ids: list[str],
        as_of_date: str,
    ) -> dict[str, Any]:
        del as_of_date
        return {
            "version": "news-evidence-mock-v1",
            "data_quality": self.data_quality,
            "evidence": [],
            "missing_narrative_ids": sorted(set(narrative_ids)),
        }


def _load_fixture(fixture_dir: Path, filename: str) -> Any:
    path = fixture_dir / filename
    if not path.exists():
        raise FixtureNotFoundError(f"Missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _mock_fixture_layer(layer: str, filename: str) -> dict[str, Any]:
    return mock_layer(layer, note=f"Loaded from V1 fixture {filename}.")
