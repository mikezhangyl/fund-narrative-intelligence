# Task Handoff

## Goal

Add explicit provider-layer interfaces for V1 intelligence sources.

## Files Changed

- `src/providers/intelligence.py`
- `src/providers/mock.py`
- `src/providers/provenance.py`
- `tests/test_intelligence_providers.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/evidence-provider-interfaces.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/runs/20260513-evidence-provider-interfaces/`

## Implementation Summary

- Added layer providers for registry, mappings, evidence, and signals.
- Added reserved empty mock providers for market data, valuation, announcements, and news evidence.
- Kept the existing `MockDataProvider` API stable by composing the new provider set internally.
- Updated provider foundation provenance to carry layer-specific fixture notes.

## Commands Run

- `python -m pytest tests/test_intelligence_providers.py -q`
- `python -m pytest tests/test_contracts.py tests/test_eastmoney_provider.py tests/test_cli_pipeline.py tests/test_intelligence_providers.py -q`
- `python -m ruff check src/providers tests/test_intelligence_providers.py`
- `python -m ruff check .`
- `python -m pytest -q`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --fund-code 000001 --output-dir /tmp/fni-provider-layer-mock`
- `python -m src.main --run-real-smoke`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-evidence-provider-interfaces --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final full test suite: 51 passed. Final coverage: 86% over `src`, above the configured 80% threshold.

## Known Risks And Assumptions

- Reserved providers are structural placeholders, not real data sources.
- Real provider implementation should preserve the explicit mock/fallback disclosure behavior.

## Suggested Quality Checks

- Re-run `python -m src.main --run-real-smoke` before merging if network availability changes.
- When adding the first real news or valuation provider, add provider-specific contract tests before integration.
