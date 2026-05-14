from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.config import FIXTURE_DIR
from src.errors import FixtureNotFoundError
from src.providers.intelligence import MockIntelligenceProviderSet
from src.providers.provenance import (
    PROVIDER_LAYERS,
    build_mock_provider_foundation,
    layer_from_provider_metadata,
)
from src.validation import validate_fund_payload


class MockDataProvider:
    """Deterministic local provider used by V1 and tests."""

    provider_name = "mock-fixture-provider"
    provider_version = "mock-v1"

    def __init__(self, fixture_dir: Path = FIXTURE_DIR):
        self.fixture_dir = fixture_dir
        self.intelligence_providers = MockIntelligenceProviderSet(
            fixture_dir=fixture_dir
        )
        self.degradation_events: list[dict[str, str]] = []

    def list_fund_codes(self) -> list[str]:
        return sorted(
            path.stem.removeprefix("fund_")
            for path in self.fixture_dir.glob("fund_*.json")
        )

    def get_fund_holdings(self, fund_code: str) -> dict[str, Any]:
        filename = f"fund_{fund_code}.json"
        payload = self._load_json(filename)
        payload = _with_mock_source_url(payload, source_url=_mock_fixture_url(filename))
        validate_fund_payload(payload, fund_code=fund_code)
        return deepcopy(payload)

    def get_narrative_registry(self) -> dict[str, Any]:
        return self.intelligence_providers.get_narrative_registry()

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        return self.intelligence_providers.get_stock_narrative_mappings()

    def get_mapping_exclusions(self) -> dict[str, Any]:
        return self.intelligence_providers.get_mapping_exclusions()

    def get_evidence(self) -> list[dict[str, Any]]:
        return self.intelligence_providers.get_evidence()

    def get_signal_events(self) -> list[dict[str, Any]]:
        return self.intelligence_providers.get_signal_events()

    def get_provider_foundation(
        self,
        fund_provider_metadata: dict[str, Any],
        degradation_events: list[dict[str, str]],
    ) -> dict[str, Any]:
        layers = {
            **build_mock_provider_foundation()["layers"],
            **self.intelligence_providers.get_provider_layers(),
        }
        layers["holdings"] = layer_from_provider_metadata(
            layer="holdings",
            provider_metadata=fund_provider_metadata,
            note="Loaded from V1 mock fund fixture.",
        )
        ordered_layers = {layer: layers[layer] for layer in PROVIDER_LAYERS}
        return build_mock_provider_foundation(
            layers=ordered_layers,
            degradation_events=degradation_events,
        )

    def _load_json(self, filename: str) -> Any:
        path = self.fixture_dir / filename
        if not path.exists():
            if filename.startswith("fund_"):
                fund_code = filename.removeprefix("fund_").removesuffix(".json")
                raise FixtureNotFoundError(
                    f"No mock fixture found for fund code {fund_code}"
                )
            raise FixtureNotFoundError(f"Missing fixture: {path}")
        return json.loads(path.read_text(encoding="utf-8"))


def _mock_fixture_url(filename: str) -> str:
    return f"mock://fixtures/{filename}"


def _with_mock_source_url(payload: dict[str, Any], source_url: str) -> dict[str, Any]:
    fund = payload["fund"]
    provider_metadata = {
        **fund["provider_metadata"],
        "source_url": source_url,
    }
    return {
        **payload,
        "fund": {
            **fund,
            "provider_metadata": provider_metadata,
        },
    }
