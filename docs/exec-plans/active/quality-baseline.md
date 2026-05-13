# Quality Baseline Execution Plan

## Purpose

Make V1 development quality gates reproducible from project metadata instead of depending on globally installed Python tools.

## Scope

- Declare Python development dependencies for tests, lint, and coverage.
- Configure pytest, ruff, and coverage in `pyproject.toml`.
- Document standard local quality commands.
- Verify the commands after installing the project development extras.

## Acceptance

- `python -m pip install -e ".[dev]"` succeeds.
- `python -m ruff check .` succeeds.
- `python -m coverage run -m pytest -q` succeeds.
- `python -m coverage report` succeeds using the configured `fail_under` threshold.
- Existing CLI acceptance commands still pass.

## Status

Implemented and locally verified.

Verification result:

- `python -m pip install -e ".[dev]"`: passed.
- `python -m ruff check .`: passed.
- `python -m pytest -q`: 42 passed.
- `python -m coverage run -m pytest -q`: 42 passed.
- `python -m coverage report`: 85% total coverage using the configured 80% threshold.
- `python -m compileall -q src tests scripts`: passed.
- `python -m src.main --fund-code 000001`: passed.
- `python -m src.main --run-all-fixtures`: passed.
- `python -m src.main --run-real-smoke`: passed.

## Run Record

- `.ecc/runs/20260513-quality-baseline/`
