# Task Handoff

## Goal

Complete Linear MIK-42 by making the Narrative Service HTTP contract explicit
about v1 endpoint policy, normalized envelope fields, additive compatibility,
and error/degraded semantics while preserving the FNI HTTP boundary.

## Files Changed

- `config/narrative_service_contract.yaml`
- `scripts/run_narrative_service_conformance_probe.py`
- `tests/test_narrative_service_conformance_probe.py`
- `docs/product/stock-narrative-service-runbook.md`
- `docs/memory/current-brief.md`

Generated verification outputs:

- `outputs/stock_narrative_service_acceptance/2026-05-28T170900+0000/acceptance_summary.json`
- `outputs/stock_narrative_service_acceptance/2026-05-28T170900+0000/conformance/narrative_service_conformance_report.json`
- `outputs/stock_narrative_service_acceptance/2026-05-28T170900+0000/provider_smoke/narrative_service_provider_smoke.json`
- `outputs/stock_narrative_service_acceptance/2026-05-28T170900+0000/fund_holding_exposure_report.json`
- `outputs/stock_narrative_service_acceptance/2026-05-28T170900+0000/fund_holding_exposure_report.html`

## Implementation Summary

Added an `api_policy` section to the Narrative Service contract with
`/api/v1/narratives` as the base path, additive/non-breaking v1 compatibility,
required envelope fields, and explicit semantics for missing ids, invalid
requests, and degraded service state. The conformance probe now prefers
`api_policy.required_envelope_fields` while preserving the existing runtime
fallback. Tests assert the policy shape and that FNI report entry points do not
import service internals. The runbook now documents versioning and error
semantics.

## Commands Run

- `uv run pytest tests/test_narrative_service_conformance_probe.py -q`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`
- `uv run pytest tests/test_narrative_service_conformance_probe.py services/stock-narrative-service/tests -q`
- `uv run pytest tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py -q`
- `uv run pytest tests/test_narrative_service_conformance_probe.py services/stock-narrative-service/tests tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py -q`
- `uv run --extra dev ruff check config tests/test_narrative_service_conformance_probe.py scripts/run_narrative_service_conformance_probe.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`

## Test Results

RED:

- Contract policy test failed with `KeyError: 'api_policy'`.

GREEN:

- `tests/test_narrative_service_conformance_probe.py`: 4 passed.
- Issue-specified service/conformance tests: 15 passed.
- Related service tests: 17 passed.
- Acceptance command status: `completed`; conformance endpoint count: 11;
  provider smoke source: `narrative_service`; report narrative source:
  `narrative_service`.
- `ruff check`: passed.
- `compileall`: passed.
- `git diff --check`: passed.

## Known Risks And Assumptions

- This formalizes v1 contract policy and validates the current in-repo service.
  It does not add authentication, deployment, or external service hosting.
- Acceptance outputs are ignored by Git; their checksums are recorded in the
  run manifest.

## Suggested Quality Checks

- Re-run `uv run python scripts/validate_stock_narrative_service_acceptance.py`
  after service endpoint changes.
- Keep adding optional endpoints/fields additively inside v1.
