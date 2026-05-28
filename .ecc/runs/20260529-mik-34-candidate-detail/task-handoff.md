# Task Handoff

## Goal

MIK-34: provide a normalized candidate narrative detail endpoint for reviewer
drill-down before review workspace and trusted-promotion work.

## Files Changed

- `config/narrative_service_contract.yaml`
- `docs/memory/current-brief.md`
- `docs/product/stock-narrative-service-runbook.md`
- `scripts/run_narrative_service_conformance_probe.py`
- `services/stock-narrative-service/src/stock_narrative_service/app.py`
- `services/stock-narrative-service/src/stock_narrative_service/storage.py`
- `services/stock-narrative-service/tests/test_http_service.py`
- `tests/test_narrative_service_conformance_probe.py`

## Implementation Summary

Added a dynamic candidate detail route under
`/api/v1/narratives/candidates/{candidate_narrative_id}`. The detail read model
combines candidate metadata, candidate trust status, full review history, latest
review action, promotion preflight gates, missing gates, recommended action, and
source evidence references. Unknown IDs now return an HTTP 200 normalized
`status=missing` envelope instead of a silent empty success or route 404.
Conformance probe now supports `conformance_path` for dynamic endpoint samples.

## Commands Run

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_candidate_detail_returns_review_history_preflight_and_evidence_refs services/stock-narrative-service/tests/test_http_service.py::test_candidate_detail_unknown_returns_missing_envelope_without_mutation -q`
- `uv run pytest tests/test_narrative_service_conformance_probe.py::test_narrative_service_contract_declares_candidate_detail_endpoint -q`
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py -q`
- `uv run pytest tests/test_narrative_service_provider.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_mapping_evidence_pack_report.py -q`
- `uv run --extra dev ruff check config tests/test_narrative_service_conformance_probe.py scripts/run_narrative_service_conformance_probe.py services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`

## Test Results

- New candidate detail tests: 2 passed.
- Candidate detail contract test: passed.
- Narrative service + conformance suite: 26 passed.
- Provider/acceptance/script/evidence report suite: 13 passed.
- Acceptance command: completed, 12 endpoints checked, provider smoke source
  `narrative_service`, generated report source `narrative_service`.
- Ruff, compileall, and diff whitespace checks passed.

## Known Risks And Assumptions

- This slice does not render a review UI; MIK-38 owns the reviewer workspace.
- Evidence pack detail is still separate and remains owned by MIK-35.
- Unknown candidate returns `status=missing` with HTTP 200 to match the contract
  policy from MIK-42.

## Suggested Quality Checks

- MIK-38 should link candidate rows to this endpoint.
- MIK-39 should consume the same preflight/missing-gate shape rather than
  recalculating gates in a new place.
