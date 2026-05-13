# Task Handoff

## Goal

Add optional CNINFO announcement provider adapter foundation.

## Files Changed

- `src/providers/cninfo.py`
- `tests/test_cninfo_provider.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/cninfo-announcement-provider.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/runs/20260513-cninfo-announcement-provider/`

## Implementation Summary

- Added CNINFO request payload builder and response normalizer.
- Added market-column selection from stock-code prefixes for SZSE, SSE, and Beijing exchange codes.
- Added `CNInfoAnnouncementProvider` with injectable fetcher.
- Added controlled unavailable fallback on fetch failures.
- Added invalid stock-code handling that avoids external requests and records degradation.
- Kept provider optional and outside default report orchestration.

## Commands Run

- `python -m pytest tests/test_cninfo_provider.py -q`
- `python -m ruff check src/providers/cninfo.py tests/test_cninfo_provider.py`
- `python -m ruff check .`
- `python -m pytest -q`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --run-real-smoke`
- Optional live CNINFO probe through `CNInfoAnnouncementProvider`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-cninfo-announcement-provider --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final coverage run executed 61 tests. Final coverage: 85% over `src`, above the configured 80% threshold.

## Known Risks And Assumptions

- CNINFO live endpoint availability is outside project control.
- Announcement-to-evidence conversion is future work.
- Default V1 report generation remains mock/eastmoney based and unchanged.

## Suggested Quality Checks

- When wiring CNINFO into orchestration, add integration tests proving `Data Source Notice` reflects CNINFO and fallback behavior.
