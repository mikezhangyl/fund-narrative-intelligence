# Task Handoff

## Goal

MIK-43: make Narrative Service ledger storage auditable, append-only, and ready
for future SQLite/Postgres migration without changing the HTTP contract.

## Files Changed

- `config/narrative_service_contract.yaml`
- `docs/memory/current-brief.md`
- `docs/product/stock-narrative-service-runbook.md`
- `services/stock-narrative-service/src/stock_narrative_service/storage.py`
- `services/stock-narrative-service/tests/test_http_service.py`
- `tests/test_narrative_service_conformance_probe.py`

## Implementation Summary

Added `storage_policy` to the Narrative Service contract with JSON-ledger
versions, required record fields, mutation rules, replay behavior, and migration
invariants. Candidate intake ledger records now include schema version, record
type, sequence, recorded timestamp, source metadata, and non-promotion effect.
Review-action records now use `narrative-review-actions-v1`, preserve actor,
timestamp, action, note, source metadata, ledger sequence, and remain
non-promotional.

## Commands Run

- `uv run pytest tests/test_narrative_service_conformance_probe.py::test_narrative_service_contract_declares_append_only_ledger_policy -q`
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_review_actions_are_append_only_and_do_not_mutate_trusted_sources services/stock-narrative-service/tests/test_http_service.py::test_failed_intake_payload_does_not_create_ledger_or_negative_cache services/stock-narrative-service/tests/test_http_service.py::test_duplicate_intake_replays_append_events_but_dedupes_candidate_reads -q`
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py -q`
- `uv run pytest tests/test_narrative_service_provider.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py -q`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`
- `uv run --extra dev ruff check config tests/test_narrative_service_conformance_probe.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`

## Test Results

- Contract ledger policy test: passed.
- New append-only runtime tests: 3 passed.
- Narrative service + conformance suite: 19 passed.
- Provider/acceptance/script tests: 10 passed.
- Acceptance command: completed, 11 endpoints checked, provider smoke source
  `narrative_service`, generated report source `narrative_service`.
- Ruff, compileall, and diff whitespace checks passed.

## Known Risks And Assumptions

- JSON-file writes still rewrite the file physically; the logical contract is
  append-only at record level.
- Promotion decisions are only reserved in the contract; MIK-44/MIK-39 should
  implement the promotion transaction path.
- Candidate identity rules remain intentionally light here; MIK-48 owns the
  stable identity model.

## Suggested Quality Checks

- Re-run Narrative Service conformance after MIK-48 adds identity rules.
- Ensure future UI/review workspace code treats review-action reads as
  append-only audit history, not current trusted state.
