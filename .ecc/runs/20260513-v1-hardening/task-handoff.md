# Task Handoff

## Goal

Harden the V1 mock pipeline before real provider integration.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

Added provider contract validation, controlled pipeline errors, fixture discovery, and local usage docs.

## Commands Run

- `python -m pytest -q`
- `python -m compileall -q src tests`
- `python -m src.main --list-fixtures`
- `python -m src.main --fund-code 000001`
- `python -m src.main --fund-code 999999`
- `python -m src.main --fund-code 000001 --provider-mode real --output-dir <tmpdir>`
- `jq empty ...`

## Test Results

12 tests passed.

## Known Risks And Assumptions

- Validation is intentionally lightweight.
- V1 remains mock-only for actual data.
- Coverage tooling is not installed.

## Suggested Quality Checks

- Re-run acceptance command after any provider changes.
- Validate real provider adapters against `src/validation.py`.
