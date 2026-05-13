# Task Brief

## Goal

Create explicit provider-layer interfaces for V1 intelligence sources and wire the mock baseline through them.

## Scope

- Add mock provider layers for narrative registry, stock mappings, evidence, and signal events.
- Add reserved mock provider interfaces for market data, valuation, announcements, and news evidence.
- Keep reserved providers honest by returning empty mock payloads rather than fabricated real data.
- Preserve existing CLI, mock fixture, Eastmoney, and report behavior.

## Out Of Scope

- Connecting real AKShare, Tushare, CNINFO, exchange, or news providers.
- Changing scoring rules.
- Changing report visual design beyond provider metadata carried forward from the previous run.

## Required Verification

- `python -m pytest tests/test_intelligence_providers.py -q`
- `python -m pytest -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python -m compileall -q src tests scripts`
- `python -m src.main --fund-code 000001`
- `python -m src.main --run-real-smoke`
