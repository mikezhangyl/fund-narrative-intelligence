# Task Handoff

## Goal

Consume stock-data-gateway narrative source events through the unified Gateway API while keeping external acquisition out of FNI.

## Files Changed

- `config/market_data_gateway_contract.yaml`
- `config/data_capabilities.yaml`
- `src/market_data/providers/narrative_source_gateway.py`
- `scripts/run_narrative_source_gateway_probe.py`
- `scripts/report_data_capabilities.py`
- `src/product_shell/source_quality.py`
- `tests/test_narrative_source_gateway_consumer.py`
- `tests/test_product_shell_source_quality.py`
- `docs/exec-plans/active/fni-gateway-source-events.md`
- `docs/exec-plans/active/index.md`
- `docs/memory/current-brief.md`

## Implementation Summary

FNI now defaults to `GET /api/v1/market-data/narrative/source-events` for narrative source-event probing and consumption. The client builds unified query parameters, preserves Gateway structured degradation, and supports the M20 source kinds `official_filings`, `official_disclosures`, `official_sources`, `news_context`, `open_news_index`, `industry_media`, and `social_heat`.

## Commands Run

- `python -m pytest tests/test_narrative_source_gateway_consumer.py -q`
- `python scripts/run_narrative_source_gateway_probe.py --base-url http://127.0.0.1:8700 --timeout-seconds 45 --limit 5 --output-dir outputs/narrative_source_gateway_probe/current`
- `python -m pytest`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`

## Test Results

- Targeted narrative source consumer tests: 7 passed.
- Related market capability/source-quality tests: 25 passed.
- Full pytest: 677 passed, 1 skipped.
- Coverage run: 677 passed, 1 skipped; total coverage 84%.
- Ruff: passed.
- Compileall: passed.
- Live Gateway probe: exit 0; 7 source kinds, 0 failed kinds, 6 rows.

## Known Risks And Assumptions

- `open_news_index` can degrade from upstream timeout/rate-limit; FNI treats Gateway's structured degraded response as non-fatal.
- `social_heat` is intentionally disabled by default and appears as structured degraded.
- Legacy per-kind POST routes remain documented for compatibility, but FNI default probing uses the unified route.
- The FNI base branch includes four existing local commits ahead of `origin/main`; this slice was branched from that current local HEAD.

## Suggested Quality Checks

- Review the unified-route query construction and degradation semantics in `src/market_data/providers/narrative_source_gateway.py`.
- Confirm product expectations for whether `official_sources` should group with official disclosures/policy or receive a separate source-quality group in a later UI slice.
