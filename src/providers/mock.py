from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from src.config import FIXTURE_DIR
from src.errors import FixtureNotFoundError
from src.validation import (
    validate_evidence_payload,
    validate_fund_payload,
    validate_mapping_payload,
    validate_registry_payload,
    validate_signal_payload,
)


class MockDataProvider:
    """Deterministic local provider used by V1 and tests."""

    provider_name = "mock-fixture-provider"
    provider_version = "mock-v1"

    def __init__(self, fixture_dir: Path = FIXTURE_DIR):
        self.fixture_dir = fixture_dir
        self.degradation_events: list[dict[str, str]] = []

    def list_fund_codes(self) -> list[str]:
        return sorted(
            path.stem.removeprefix("fund_")
            for path in self.fixture_dir.glob("fund_*.json")
        )

    def get_fund_holdings(self, fund_code: str) -> dict[str, Any]:
        payload = self._load_json(f"fund_{fund_code}.json")
        validate_fund_payload(payload, fund_code=fund_code)
        return deepcopy(payload)

    def get_narrative_registry(self) -> dict[str, Any]:
        payload = self._load_json("narrative_registry.json")
        validate_registry_payload(payload)
        return deepcopy(payload)

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        payload = self._load_json("stock_narrative_mappings.json")
        validate_mapping_payload(payload)
        return deepcopy(payload["mappings"])

    def get_evidence(self) -> list[dict[str, Any]]:
        payload = self._load_json("evidence.json")
        validate_evidence_payload(payload)
        return deepcopy(payload["evidence"])

    def get_signal_events(self) -> list[dict[str, Any]]:
        payload = self._load_json("signal_events.json")
        validate_signal_payload(payload)
        return deepcopy(payload["signal_events"])

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
