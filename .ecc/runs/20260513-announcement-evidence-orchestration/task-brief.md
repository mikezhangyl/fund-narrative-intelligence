# Task Brief

## Goal

Expose optional CNINFO announcement evidence orchestration with explicit provider disclosure.

## Scope

- Add `--include-cninfo-announcements` CLI opt-in.
- Add optional `--announcement-start-date`.
- Keep default report generation unchanged.
- Fetch announcement metadata only when explicitly requested.
- Convert announcement metadata into evidence records through the existing converter.
- Add an `Announcements` provider-foundation layer in raw/scoring JSON and reports.

## Out Of Scope

- Default-on CNINFO usage.
- PDF download or parsing.
- Signal generation from announcement evidence.
- Historical replay or alerting.

## Required Verification

- `python -m pytest tests/test_cli_pipeline.py -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --run-real-smoke`
- `python -m src.main --fund-code 000001 --include-cninfo-announcements --announcement-start-date 2026-05-01`
- `python -m src.main --fund-code 161725 --provider-mode eastmoney --include-cninfo-announcements --announcement-start-date 2026-05-01`
