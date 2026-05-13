# Task Handoff

## Goal

Calibrate V1 real-fund smoke scoring so the fixed Eastmoney smoke set produces differentiated narrative lifecycle stages.

## Files Changed

- `src/modules/signal_service/scoring.py`
- `data/fixtures/signal_events.json`
- `tests/test_real_fund_calibration.py`
- `tests/test_multi_fixture_scenarios.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/index.md`
- `docs/exec-plans/active/real-fund-expansion.md`
- `docs/exec-plans/active/real-fund-scoring-calibration.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/framework-state.json`
- `.ecc/runs/20260513-real-fund-scoring-calibration/`

## Implementation Summary

- Added a real-fund calibration regression for the intended six-fund distribution.
- Added a semiconductor momentum fixture and calibrated deterministic stage thresholds.
- Preserved the three mock fixture scenario stages: `000001` strengthening, `000002` crowded, and `000003` dead.
- Updated durable project docs and run records with the calibrated smoke baseline.

## Commands Run

- `python -m pytest tests/test_real_fund_calibration.py tests/test_scoring.py tests/test_multi_fixture_scenarios.py -q`
- `python -m src.main --run-real-smoke`
- `python -m src.main --fund-code 000001`
- `python -m src.main --run-all-fixtures`
- `python -m ruff check .`
- `python -m pytest -q`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-real-fund-scoring-calibration --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final full test suite: 44 passed. Final coverage: 85% over `src`, above the configured 80% threshold.

## Known Risks And Assumptions

- The real-smoke command depends on the public Eastmoney holdings response and can drift as holdings update.
- Real-fund scoring still uses local fixture-backed signals and evidence in V1.
- The integrated real-smoke command verifies the current provider path; the direct calibration test keeps stage-rule expectations deterministic.

## Suggested Quality Checks

- Re-run `python -m src.main --run-real-smoke` before publishing if the branch sits for more than a day.
- When replacing fixture-backed signals with real providers, validate the six-fund distribution before accepting changed stage semantics.
