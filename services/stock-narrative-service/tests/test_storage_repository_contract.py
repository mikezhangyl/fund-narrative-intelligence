from __future__ import annotations

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SERVICE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from stock_narrative_service.repository import (  # noqa: E402
    JsonLedgerNarrativeRepository,
    repository_contract_methods,
    validate_repository_contract,
)
from stock_narrative_service.storage import NarrativeStore  # noqa: E402
from test_http_service import _write_seed_files  # noqa: E402


def test_json_ledger_repository_matches_current_store_contract(tmp_path):
    config = _write_seed_files(tmp_path)
    repository = JsonLedgerNarrativeRepository(config)
    store = NarrativeStore(config)

    validate_repository_contract(repository)
    assert repository.storage_backend == "json_file_ledgers_v1"
    assert repository.registry() == store.registry()
    assert repository.mappings() == store.mappings()
    assert repository.review_queue() == store.review_queue()
    assert repository.review_actions() == store.review_actions()


def test_future_repository_interface_contract_is_explicit():
    methods = repository_contract_methods()

    assert methods == (
        "registry",
        "mappings",
        "evidence_packs",
        "candidates",
        "review_queue",
        "review_actions",
        "promotion_decisions",
        "ops_summary",
    )
    validate_repository_contract(FakeSQLiteReadyRepository())


class FakeSQLiteReadyRepository:
    storage_backend = "sqlite_future"

    def registry(self):
        return {}

    def mappings(self):
        return {}

    def evidence_packs(self):
        return {}

    def candidates(self):
        return {}

    def review_queue(self, *, status: str = ""):
        return {"status": status}

    def review_actions(self):
        return {}

    def promotion_decisions(self):
        return {}

    def ops_summary(self):
        return {}
