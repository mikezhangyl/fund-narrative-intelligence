# Task Brief

## Goal

Reduce clear real-smoke `broad_industry_fallback` rows by adding company-level registry terms.

## Scope

- Extract current broad fallback rows from real-smoke outputs.
- Add a regression test for clear company-level curation candidates.
- Update `narrative_registry.json` with specific company terms where the narrative relationship is clear.
- Leave ambiguous semiconductor broad flags visible for follow-up.

## Acceptance

- Clear curated candidates no longer emit `broad_industry_fallback`.
- Real-smoke broad fallback count is reduced while preserving 100% coverage and calibrated stages.
- Full quality gates and live smoke commands pass.

## Verification

- `python -m pytest tests/test_mapping_coverage.py -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Outcome

The fixed real-smoke set still passes with 100% mapping coverage and stable calibrated stages. Clear broad industry-only fallback rows were reduced, leaving 3 intentionally unresolved Semiconductor Capex broad flags: `600522` 中天科技, `688036` 传音控股, and `688692` 达梦数据.
