# Task Brief

## Goal

Add an optional CNINFO announcement provider adapter foundation.

## Scope

- Build CNINFO announcement query payloads.
- Normalize CNINFO announcement responses into the V1 announcement-provider contract.
- Use injectable fetchers for deterministic tests.
- Return controlled `unavailable` payloads and `provider_unavailable` degradation events on fetch failure.
- Keep the default report pipeline unchanged.

## Out Of Scope

- Default orchestration integration.
- PDF downloading or parsing.
- Announcement-to-signal scoring.
- Buy/sell interpretation.

## Required Verification

- `python -m pytest tests/test_cninfo_provider.py -q`
- `python -m pytest -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
