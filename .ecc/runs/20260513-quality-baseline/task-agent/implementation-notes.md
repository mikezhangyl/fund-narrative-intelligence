# Implementation Notes

## Summary

Made the Python quality baseline reproducible from project metadata.

## Changes

- Added pinned `dev` dependencies for `pytest`, `ruff`, and `coverage`.
- Added `pyproject.toml` configuration for pytest, ruff, and coverage.
- Added coverage branch tracking with an 80% configured threshold over `src`.
- Added README quality commands and project memory / ADR documentation.
- Added tests for the quality configuration contract.
- Added direct `main()` CLI tests so coverage includes CLI branches that subprocess tests cannot measure.
- Ran ruff auto-fix for import ordering and unused imports.
- Updated `.gitignore` for `.venv/`, `.coverage*`, and generated `outputs/`.

## Reviewer Fixes

- Reviewer flagged open-ended dev dependency lower bounds. Fixed by pinning exact tool versions.
- Reviewer flagged README hardcoding `--fail-under=80` as a second threshold source. Fixed by documenting `python -m coverage report` and keeping the threshold only in `pyproject.toml`.

## Result

The project now supports `python -m pip install -e ".[dev]"` followed by reproducible lint, test, coverage, and compile gates.
