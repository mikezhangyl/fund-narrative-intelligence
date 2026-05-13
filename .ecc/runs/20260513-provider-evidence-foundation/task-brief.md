# Task Brief

## Goal

Add a provider/evidence foundation that separates provenance by data layer and visibly discloses mock, degraded, or mixed real/mock data in user-facing reports.

## Scope

- Add `provider_foundation` metadata to raw and scoring JSON.
- Use `provider_foundation.effective_data_quality` for scoring/report metadata.
- Ensure mock runs and fallback-to-mock runs are clearly disclosed in Markdown and HTML.
- Mark Eastmoney-holdings plus fixture-backed intelligence layers as `partial`.
- Extend real-fund smoke summary output with effective data quality and disclosure status.

## Out Of Scope

- Adding real evidence, news, valuation, announcement, or signal providers.
- Adding a frontend workspace.
- Changing investment interpretation semantics or adding buy/sell recommendations.

## Required Verification

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python -m compileall -q src tests scripts`
- `python -m src.main --fund-code 000001`
- `python -m src.main --fund-code 000001 --provider-mode real`
- `python -m src.main --run-real-smoke`
