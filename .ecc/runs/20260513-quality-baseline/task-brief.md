# Task Brief

## Goal

Make test, lint, and coverage gates reproducible through project-level Python metadata.

## Scope

- Add project dev dependencies for `pytest`, `ruff`, and `coverage`.
- Add tool configuration for pytest, ruff, and coverage.
- Add tests that guard the quality tooling contract.
- Update README and project memory with standard commands.
- Run quality gates after installing dev extras.

## Out Of Scope

- Changing scoring or provider logic.
- Adding frontend tooling.
- Creating a commit or PR unless explicitly requested.

## Required Verification

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python -m compileall -q src tests scripts`
- CLI smoke commands for mock and real-provider paths where practical.
