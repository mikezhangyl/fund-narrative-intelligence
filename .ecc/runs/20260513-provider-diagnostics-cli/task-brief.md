# Task Brief

## Goal

Add a CLI diagnostics path for provider foundation metadata without generating report artifacts.

## Scope

- Add `--provider-diagnostics`.
- Print provider foundation JSON for a selected `fund_code` and `provider_mode`.
- Ensure diagnostics does not write files under the requested output directory.
- Surface `provider_fallback` for `real` mode.
- Document the command.

## Out Of Scope

- Adding new real providers.
- Changing report generation.
- Changing scoring rules.

## Required Verification

- `python -m pytest tests/test_provider_diagnostics.py -q`
- `python -m pytest -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python -m compileall -q src tests scripts`
- `python -m src.main --fund-code 000001 --provider-diagnostics`
- `python -m src.main --run-real-smoke`
