# Task Handoff

## Goal

MIK-48: define stable ID rules so later candidate/evidence detail endpoints and
review UI links do not invent their own identifiers.

## Files Changed

- `config/narrative_service_contract.yaml`
- `docs/memory/current-brief.md`
- `docs/product/stock-narrative-service-runbook.md`
- `services/stock-narrative-service/src/stock_narrative_service/identity.py`
- `services/stock-narrative-service/src/stock_narrative_service/storage.py`
- `services/stock-narrative-service/tests/test_http_service.py`
- `tests/test_narrative_service_conformance_probe.py`

## Implementation Summary

Added a dedicated identity helper module. Runtime now preserves explicit IDs and
derives deterministic fallback IDs for source events, intake candidates,
stock+narrative evidence packs, candidate mappings, and review actions. Review
actions with an idempotency key replay an existing decision instead of appending
a duplicate record. Evidence pack reads now expose stable mapping/detail IDs for
future drill-down endpoints.

## Commands Run

- `uv run pytest tests/test_narrative_service_conformance_probe.py::test_narrative_service_contract_declares_identity_policy -q`
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_intake_fallback_identity_is_stable_for_links_and_duplicate_reads services/stock-narrative-service/tests/test_http_service.py::test_review_action_idempotency_key_replays_without_append services/stock-narrative-service/tests/test_http_service.py::test_evidence_packs_expose_stable_pack_and_mapping_ids -q`
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py -q`
- `uv run pytest tests/test_narrative_service_provider.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_mapping_evidence_pack_report.py -q`
- `uv run --extra dev ruff check config tests/test_narrative_service_conformance_probe.py services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`

## Test Results

- Contract identity policy test: passed.
- New runtime identity/idempotency tests: 3 passed.
- Narrative service + conformance suite: 23 passed.
- Provider/acceptance/script/evidence report suite: 13 passed.
- Acceptance command: completed, 11 endpoints checked, provider smoke source
  `narrative_service`, generated report source `narrative_service`.
- Ruff, compileall, and diff whitespace checks passed.

## Known Risks And Assumptions

- Detail endpoints are not added in this slice; MIK-34 and MIK-35 consume these
  IDs.
- Promotion decision IDs are reserved but not persisted until the promotion
  boundary/workflow tasks.
- Existing explicit IDs are preserved even if they do not match the new prefix
  conventions.

## Suggested Quality Checks

- MIK-34 should use `candidate_narrative_id` directly for candidate detail.
- MIK-35 should accept `evidence_pack_id` or stock+narrative query fields and
  verify both resolve to the same pack.
