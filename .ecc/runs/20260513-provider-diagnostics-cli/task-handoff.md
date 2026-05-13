# Task Handoff

## Goal

Expose provider foundation diagnostics from the CLI.

## Files Changed

- `src/main.py`
- `src/orchestrator.py`
- `tests/test_cli_pipeline.py`
- `tests/test_provider_diagnostics.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/provider-diagnostics-cli.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/runs/20260513-provider-diagnostics-cli/`

## Implementation Summary

- Added `--provider-diagnostics`.
- Prints JSON provider foundation metadata for the selected fund and provider mode.
- Validates that diagnostics does not write report artifacts.
- Shows fallback events for `real` mode.

## Commands Run

- `python -m pytest tests/test_cli_pipeline.py::test_cli_provider_diagnostics_prints_foundation_without_artifacts tests/test_cli_pipeline.py::test_cli_provider_diagnostics_shows_real_mode_fallback -q`
- `python -m pytest tests/test_provider_diagnostics.py tests/test_cli_pipeline.py::test_cli_provider_diagnostics_prints_foundation_without_artifacts tests/test_cli_pipeline.py::test_cli_provider_diagnostics_shows_real_mode_fallback -q`
- `python -m ruff check .`
- `python -m pytest -q`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m compileall -q src tests scripts`
- `python -m src.main --fund-code 000001 --provider-diagnostics --output-dir /tmp/fni-provider-diagnostics-check`
- `python -m src.main --run-real-smoke`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-provider-diagnostics-cli --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final full test suite: 55 passed. Final coverage: 85% over `src`, above the configured 80% threshold.

## Known Risks And Assumptions

- Diagnostics for live provider modes can still depend on external provider availability.
- The command is intended for provider inspection, not report generation.

## Suggested Quality Checks

- Re-run diagnostics with `--provider-mode real` or `--provider-mode eastmoney` when adding real provider layers.
