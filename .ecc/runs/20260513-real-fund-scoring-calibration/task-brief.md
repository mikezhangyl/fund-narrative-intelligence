# Task Brief

## Goal

Calibrate V1 real-fund smoke scoring so the fixed Eastmoney smoke set produces differentiated narrative lifecycle stages.

## Scope

- Inspect current primary narrative scores and signal drivers.
- Add tests that encode the expected stage distribution.
- Adjust fixture-backed signal evidence and stage logic where justified.
- Preserve deterministic mock-provider tests and real-provider smoke behavior.

## Out Of Scope

- Adding new real news, valuation, or financial providers.
- Using LLMs for scoring.
- Producing buy/sell recommendations.

## Required Verification

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
