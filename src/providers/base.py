from __future__ import annotations

from typing import Any, Protocol


class DataProvider(Protocol):
    provider_name: str
    provider_version: str
    degradation_events: list[dict[str, str]]

    def get_fund_holdings(self, fund_code: str) -> dict[str, Any]:
        raise NotImplementedError

    def get_narrative_registry(self) -> dict[str, Any]:
        raise NotImplementedError

    def get_stock_narrative_mappings(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_evidence(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_signal_events(self) -> list[dict[str, Any]]:
        raise NotImplementedError
