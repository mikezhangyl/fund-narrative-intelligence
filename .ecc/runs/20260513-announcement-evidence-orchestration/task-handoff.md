# Task Handoff

## Goal

Add optional CNINFO announcement evidence orchestration with explicit user-facing source disclosure.

## Files Changed

- `src/main.py`
- `src/orchestrator.py`
- `src/providers/cninfo.py`
- `src/providers/intelligence.py`
- `src/providers/provenance.py`
- `tests/test_cli_pipeline.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/announcement-evidence-orchestration.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/runs/20260513-announcement-evidence-orchestration/`

## Implementation Summary

- Added `--include-cninfo-announcements`.
- Added optional `--announcement-start-date`.
- Wired opt-in announcement metadata through the existing announcement evidence converter.
- Added `Announcements` provider-foundation layer support.
- Preserved default mock-first report behavior.

## Commands Run

- `python -m pytest tests/test_cli_pipeline.py -q`
- `python -m pytest tests/test_cli_pipeline.py tests/test_intelligence_providers.py -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --run-real-smoke`
- `python -m src.main --fund-code 000001 --include-cninfo-announcements --announcement-start-date 2026-05-01`
- `python -m src.main --fund-code 161725 --provider-mode eastmoney --include-cninfo-announcements --announcement-start-date 2026-05-01`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-announcement-evidence-orchestration --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final coverage run executed 69 tests. Final coverage: 85% over `src`, above the configured 80% threshold.

## Known Risks And Assumptions

- CNINFO availability is outside project control.
- Announcement evidence is metadata-only.
- Signal events remain fixture-backed until a later signal-generation phase.

## Suggested Quality Checks

- Find real A-share funds and date windows with non-empty CNINFO announcements.
- Add regression fixtures for non-empty announcement result windows before deriving signal events from announcement evidence.
