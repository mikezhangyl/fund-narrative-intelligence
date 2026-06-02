# Task Handoff

## Goal

Finish MIK-224 by making the licensed news and market-intelligence provider
evaluation pack explicit in JSON and visible in the Chinese HTML report.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds provider-level evaluation packs for Wind, Choice, iFinD,
LSEG/Reuters, RavenPack, AlphaSense, Benzinga, Finnhub, and Tushare news
permissions. Each row records trial/contact path, API availability,
cost/contract notes, market coverage, dataset categories, and official source
links.

The matrix HTML now includes a `Provider trial/API 评估` table so the PM review
surface is readable without opening JSON. Provider facts are limited to official
vendor pages discovered during this slice; no unconfirmed pricing is invented.

## Commands Run

- `uv run pytest tests/test_narrative_source_decision_matrix.py -q`
- `uv run python scripts/run_narrative_source_decision_matrix.py --output-dir outputs/narrative_source_decision_matrix/current`
- `uv run ruff check .`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest tests/test_narrative_source_decision_matrix.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `661 passed, 1 skipped`.

## Known Risks And Assumptions

Commercial pricing, contract terms, redistribution rights, and credentialed
trial/live smoke still require PM or vendor confirmation before Gateway adapter
implementation.

## Suggested Quality Checks

- PM should verify the official contact paths and decide which China-first and
  global/news-analytics provider proceeds to trial smoke.
