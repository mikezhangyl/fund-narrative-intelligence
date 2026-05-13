# Task Handoff

## Goal

Add optional announcement-to-evidence conversion.

## Files Changed

- `src/modules/evidence/announcements.py`
- `src/modules/evidence/__init__.py`
- `tests/test_announcement_evidence.py`
- `README.md`
- `docs/product/v1-implementation-spec.md`
- `docs/exec-plans/active/announcement-evidence-conversion.md`
- `docs/memory/project-context.md`
- `docs/memory/architecture-decisions.md`
- `.ecc/runs/20260513-announcement-evidence-conversion/`

## Implementation Summary

- Added deterministic conversion from CNINFO-style announcement metadata into V1 evidence records.
- Mapped announcement stock codes through existing stock narrative mappings.
- Added conservative keyword classification for positive, risk, mixed, and generic announcement evidence.
- Included provider data quality and mapping confidence in generated confidence.
- Kept the converter optional and outside the default report pipeline.

## Commands Run

- `python -m pytest tests/test_announcement_evidence.py -q`
- `python -m ruff check src/modules/evidence/announcements.py tests/test_announcement_evidence.py`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --run-real-smoke`
- `python -m src.main --fund-code 000001`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260513-announcement-evidence-conversion --require-task-artifacts --require-quality-artifacts`

## Test Results

All required checks passed. Final coverage run executed 66 tests. Final coverage: 85% over `src`, above the configured 80% threshold.

## Known Risks And Assumptions

- The converter uses metadata only and does not parse source PDFs.
- The converter is not wired into default reports.
- Generated announcement evidence should not reach user-facing reports until provider foundation disclosure includes the announcement layer.

## Suggested Quality Checks

- When wiring announcement evidence into orchestration, add integration tests proving `Data Source Notice` includes announcement provider provenance.
- Before scoring generated announcement evidence, review real announcement samples and tune keyword rules against false positives.
