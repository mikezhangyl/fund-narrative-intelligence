# Task Handoff

## Goal

MIK-35: provide a reviewer-facing evidence pack detail read model for
stock-to-narrative mapping validation.

## Files Changed

- `config/narrative_service_contract.yaml`
- `docs/memory/current-brief.md`
- `docs/product/stock-narrative-service-runbook.md`
- `services/stock-narrative-service/src/stock_narrative_service/app.py`
- `services/stock-narrative-service/src/stock_narrative_service/storage.py`
- `services/stock-narrative-service/tests/test_http_service.py`
- `tests/test_narrative_service_conformance_probe.py`

## Implementation Summary

Added evidence pack detail lookup by stable `evidence_pack_id` and by
`stock_code` + `narrative_id` query fields. The read model returns mapping
rationale, exclusion rationale, confidence components, normalized evidence item
source fields, supported claim types, and `promotion_effect=none`. Missing packs
return a normalized `status=missing` envelope and do not write review, intake,
registry, mapping, or evidence files.

## Commands Run

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_evidence_pack_detail_by_stock_and_narrative_returns_source_drilldown services/stock-narrative-service/tests/test_http_service.py::test_evidence_pack_detail_by_pack_id_matches_stock_narrative_lookup services/stock-narrative-service/tests/test_http_service.py::test_evidence_pack_detail_missing_returns_missing_envelope_without_mutation -q`
- `uv run pytest tests/test_narrative_service_conformance_probe.py::test_narrative_service_contract_declares_evidence_pack_detail_endpoint -q`
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py -q`
- `uv run pytest tests/test_narrative_service_provider.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_mapping_evidence_pack_report.py -q`
- `uv run --extra dev ruff check config tests/test_narrative_service_conformance_probe.py scripts/run_narrative_service_conformance_probe.py services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`

## Test Results

- New evidence detail tests: 3 passed.
- Evidence detail contract test: passed.
- Narrative service + conformance suite: 30 passed.
- Provider/acceptance/script/evidence report suite: 13 passed.
- Acceptance command: completed, 13 endpoints checked, provider smoke source
  `narrative_service`, generated report source `narrative_service`.
- Ruff, compileall, and diff whitespace checks passed.

## Known Risks And Assumptions

- This endpoint is read-only and does not promote mappings.
- Human review workspace remains pending in MIK-38.
- Trusted promotion transaction semantics remain pending in MIK-44/MIK-39.

## Suggested Quality Checks

- MIK-38 should link evidence rows to both evidence-pack-id and stock+narrative
  query forms.
- MIK-39 should require promotion to read this evidence shape rather than
  trusting mapping records directly.
