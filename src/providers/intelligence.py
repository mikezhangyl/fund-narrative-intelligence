from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

from src.config import (
    DEFAULT_REVIEWED_REGISTRY_PATH,
    DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH,
    FIXTURE_DIR,
    PROJECT_ROOT,
)
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
class ReviewedNarrativeRegistryProvider:
    registry_path: Path = DEFAULT_REVIEWED_REGISTRY_PATH

    provider_name = "reviewed-registry-store"
    provider_version = "reviewed-registry-v1"
    data_quality = "fresh"

    def get_narrative_registry(self) -> dict[str, Any]:
        payload = _load_json_object(self.registry_path)
        validate_registry_payload(payload)
        _require_reviewed_registry_metadata(payload)
        return deepcopy(payload)

    def get_provider_layer(self) -> dict[str, Any]:
        payload = _load_json_object(self.registry_path)
        _require_reviewed_store_metadata(payload, context="reviewed registry")
        return {
            "layer": "narrative_registry",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": self.data_quality,
            "source_url": _reviewed_registry_source_url(self.registry_path),
            "is_mock": False,
            "note": "Loaded from file-backed Narrative Registry store for reviewed workflows.",
            "review_metadata": deepcopy(payload["review_metadata"]),
        }


@dataclass(frozen=True)
class ReviewedStockNarrativeMappingProvider:
    mappings_path: Path = DEFAULT_REVIEWED_STOCK_MAPPINGS_PATH

    provider_name = "reviewed-mapping-store"
    provider_version = "reviewed-mapping-v1"
    data_quality = "partial"

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        payload = _load_json_object(self.mappings_path, label="reviewed mappings")
        validate_mapping_payload(payload)
        _require_reviewed_store_metadata(payload, context="reviewed mappings")
        _require_reviewed_mapping_entry_metadata(payload["mappings"])
        _require_reviewed_mapping_methods(payload["mappings"])
        return deepcopy(payload["mappings"])

    def get_provider_layer(self) -> dict[str, Any]:
        payload = _load_json_object(self.mappings_path, label="reviewed mappings")
        _require_reviewed_store_metadata(payload, context="reviewed mappings")
        return {
            "layer": "stock_mappings",
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "data_quality": self.data_quality,
            "source_url": _reviewed_source_url(
                scheme="reviewed-mapping",
                path=self.mappings_path,
            ),
            "is_mock": False,
            "note": "Loaded from file-backed stock-to-narrative mapping store for reviewed workflows.",
            "review_metadata": deepcopy(payload["review_metadata"]),
        }


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


def _load_json_object(path: Path, label: str = "reviewed registry") -> dict[str, Any]:
    if not path.exists():
        raise FixtureNotFoundError(f"Missing {label}: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _reviewed_registry_source_url(path: Path) -> str:
    return _reviewed_source_url(scheme="reviewed-registry", path=path)


def _require_reviewed_registry_metadata(payload: dict[str, Any]) -> None:
    _require_reviewed_store_metadata(payload, context="reviewed registry")
    for index, narrative in enumerate(payload["narratives"]):
        if narrative.get("human_review_status") != "approved":
            continue
        _require_review_fields(narrative, context=f"narratives[{index}]")


def _require_reviewed_store_metadata(payload: dict[str, Any], context: str) -> None:
    metadata = payload.get("review_metadata")
    if not isinstance(metadata, dict):
        raise ValueError(f"{context} must include review_metadata")
    required = {"review_schema_version", "reviewed_by", "reviewed_at", "review_note"}
    missing = sorted(required - set(metadata))
    if missing:
        raise ValueError(
            f"{context}.review_metadata missing fields: {', '.join(missing)}"
        )
    if metadata.get("review_schema_version") != "review-metadata-v1":
        raise ValueError(
            f"{context}.review_metadata.review_schema_version must be review-metadata-v1"
        )
    _require_review_fields(metadata, context=f"{context}.review_metadata")
    review_note = metadata.get("review_note")
    if not isinstance(review_note, str) or not review_note.strip():
        raise ValueError(f"{context}.review_metadata.review_note must be a non-empty string")


def _require_reviewed_mapping_entry_metadata(mappings: list[dict[str, Any]]) -> None:
    for index, mapping in enumerate(mappings):
        review = mapping.get("review")
        if not isinstance(review, dict):
            raise ValueError(f"mappings[{index}] must include review metadata")
        if review.get("status") != "approved":
            raise ValueError(f"mappings[{index}].review.status must be approved")
        _require_review_fields(review, context=f"mappings[{index}].review")


def _require_review_fields(payload: dict[str, Any], context: str) -> None:
    for field in ("reviewed_by", "reviewed_at"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{context}.{field} must be a non-empty string")


def _require_reviewed_mapping_methods(mappings: list[dict[str, Any]]) -> None:
    invalid_methods = sorted(
        {
            str(mapping.get("method"))
            for mapping in mappings
            if mapping.get("method") != "reviewed_mapping"
        }
    )
    if invalid_methods:
        raise ValueError(
            "reviewed mapping store entries must use method reviewed_mapping; "
            f"found: {', '.join(invalid_methods)}"
        )


def _reviewed_source_url(scheme: str, path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        location = resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        path_hash = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        location = f"external/{path_hash}/{resolved.name}"
    content_hash = _file_sha256(resolved)[:12] if resolved.exists() else "missing"
    return f"{scheme}://{quote(location, safe='/._-')}#sha256={content_hash}"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mock_fixture_layer(layer: str, filename: str) -> dict[str, Any]:
    return mock_layer(
        layer,
        note=f"Loaded from V1 fixture {filename}.",
        source_url=f"mock://fixtures/{filename}",
    )
