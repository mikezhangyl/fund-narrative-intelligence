from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from stock_narrative_service.config import ServiceConfig
from stock_narrative_service.storage import NarrativeStore


@runtime_checkable
class NarrativeRepository(Protocol):
    storage_backend: str

    def registry(self) -> dict[str, Any]: ...

    def mappings(self) -> dict[str, Any]: ...

    def evidence_packs(self) -> dict[str, Any]: ...

    def candidates(self) -> dict[str, Any]: ...

    def review_queue(self, *, status: str = "") -> dict[str, Any]: ...

    def review_actions(self) -> dict[str, Any]: ...

    def promotion_decisions(self) -> dict[str, Any]: ...

    def ops_summary(self) -> dict[str, Any]: ...


class JsonLedgerNarrativeRepository:
    storage_backend = "json_file_ledgers_v1"

    def __init__(self, config: ServiceConfig):
        self._store = NarrativeStore(config)

    def registry(self) -> dict[str, Any]:
        return self._store.registry()

    def mappings(self) -> dict[str, Any]:
        return self._store.mappings()

    def evidence_packs(self) -> dict[str, Any]:
        return self._store.evidence_packs()

    def candidates(self) -> dict[str, Any]:
        return self._store.candidates()

    def review_queue(self, *, status: str = "") -> dict[str, Any]:
        return self._store.review_queue(status=status)

    def review_actions(self) -> dict[str, Any]:
        return self._store.review_actions()

    def promotion_decisions(self) -> dict[str, Any]:
        return self._store.promotion_decisions()

    def ops_summary(self) -> dict[str, Any]:
        return self._store.ops_summary()


def repository_contract_methods() -> tuple[str, ...]:
    return (
        "registry",
        "mappings",
        "evidence_packs",
        "candidates",
        "review_queue",
        "review_actions",
        "promotion_decisions",
        "ops_summary",
    )


def validate_repository_contract(repository: Any) -> None:
    if not isinstance(getattr(repository, "storage_backend", ""), str):
        raise TypeError("repository.storage_backend must be a string")
    for method in repository_contract_methods():
        if not callable(getattr(repository, method, None)):
            raise TypeError(f"repository missing callable method: {method}")
