## Goal

Clean FNI narrative source boundaries after gateway-side narrative source
acceptance passed.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

Removed direct Round 13 source acquisition pilots from FNI: SEC EDGAR, CNINFO
disclosure classification, public-news context, and Stocktwits heat smoke.
Added a boundary regression test that blocks those pilots from returning. Kept
the gateway consumer/probe/tests as the FNI-owned source integration surface.
Changed the legacy CNINFO announcement provider so it no longer performs live
CNINFO acquisition by default; fixture-injected fetchers remain supported.

## Commands Run

- `uv run pytest tests/test_narrative_source_boundary.py`
- `uv run pytest tests/test_narrative_source_boundary.py tests/test_cninfo_provider.py tests/test_narrative_source_gateway_consumer.py`
- `uv run pytest tests/test_narrative_source_boundary.py tests/test_narrative_source_gateway_consumer.py tests/test_source_governance_model.py tests/test_source_schema_v2.py tests/test_source_reliability_scoring.py`
- `uv run pytest`

## Test Results

Full test suite passed: `597 passed, 1 skipped`.

## Known Risks And Assumptions

Older FNI providers such as EastMoney, Tushare compatibility, and Google/Sina
news evidence are historical surfaces outside this cleanup slice. This slice
only removes the Round 13 narrative source pilots that gateway has replaced.

## Suggested Quality Checks

- `uv run ruff check .`
- `git diff --check`
- Optional live FNI probe against gateway after gateway is restarted on port
  `8700`.
