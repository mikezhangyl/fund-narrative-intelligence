# Task Brief

## Goal

Clean FNI narrative source boundaries after gateway-side narrative source
acceptance passed. Remove direct Round 13 source acquisition pilots from FNI and
keep only the gateway consumer/probe surface.

## Scope

- Delete direct SEC EDGAR, CNINFO disclosure classifier, public-news context, and
  Stocktwits heat pilot code, scripts, and tests.
- Add a boundary regression test so those direct source pilots do not reappear.
- Keep the gateway consumer contract/probe/tests.
- Degrade the legacy CNINFO announcement provider so it no longer performs live
  CNINFO acquisition by default; injected fixture fetchers still work for
  historical tests.

## Verification

- `uv run pytest tests/test_narrative_source_boundary.py`
- `uv run pytest tests/test_narrative_source_boundary.py tests/test_cninfo_provider.py tests/test_narrative_source_gateway_consumer.py`
- `uv run pytest tests/test_narrative_source_boundary.py tests/test_narrative_source_gateway_consumer.py tests/test_source_governance_model.py tests/test_source_schema_v2.py tests/test_source_reliability_scoring.py`
- `uv run pytest`
