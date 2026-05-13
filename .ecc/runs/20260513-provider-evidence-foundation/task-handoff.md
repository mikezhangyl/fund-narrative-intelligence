# Task Handoff

## Goal

Make mock, degraded, and mixed real/mock provider usage visible in user-facing outputs.

## Files Changed

- `src/providers/provenance.py`
- `src/providers/base.py`
- `src/providers/mock.py`
- `src/providers/eastmoney.py`
- `src/orchestrator.py`
- `src/modules/report_writer/writer.py`
- `src/real_fund_smoke.py`
- `tests/test_cli_pipeline.py`
- `tests/test_eastmoney_provider.py`
- `tests/test_report_writer.py`
- `tests/test_real_fund_smoke.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/provider-evidence-foundation.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/runs/20260513-provider-evidence-foundation/`

## Implementation Summary

- Added run-level `provider_foundation` metadata with provenance for holdings, registry, stock mappings, evidence, and signals.
- Reports now render `Data Source Notice` for mock, fallback, or mixed runs.
- Eastmoney holdings with mock intelligence layers are scored and reported as `partial`.
- Real smoke summaries now show data quality and whether a data source notice is required.

## Commands Run

- `python -m pytest tests/test_cli_pipeline.py tests/test_report_writer.py tests/test_real_fund_smoke.py -q`
- `python -m pytest tests/test_eastmoney_provider.py tests/test_cli_pipeline.py tests/test_report_writer.py tests/test_real_fund_smoke.py -q`
- `python -m ruff check .`
- `python -m pytest -q`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --fund-code 000001 --output-dir /tmp/fni-final-mock`
- `python -m src.main --fund-code 000001 --provider-mode real --output-dir /tmp/fni-final-real-fallback`
- `python -m src.main --run-real-smoke`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-provider-evidence-foundation --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final full test suite: 46 passed. Final coverage: 85% over `src`, above the configured 80% threshold. Live Eastmoney smoke passed and produced `partial` / `Notice=yes` summary rows.

## Known Risks And Assumptions

- Network-backed Eastmoney smoke can fail if the public endpoint or local network is unavailable.
- Real evidence/signal providers remain future work.
- The current output contract favors explicit disclosure over pretending mixed runs are fully real.

## Suggested Quality Checks

- Before merging, re-run `python -m src.main --run-real-smoke` if network availability changed.
- When adding a UI, render the same `provider_foundation.disclosure_message` prominently.
