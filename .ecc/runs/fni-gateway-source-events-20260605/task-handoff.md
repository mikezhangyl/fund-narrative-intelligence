# Task Handoff

## Goal

Consume stock-data-gateway narrative source events through the unified Gateway API while keeping external acquisition out of FNI.

## Files Changed

- `config/market_data_gateway_contract.yaml`
- `config/data_capabilities.yaml`
- `src/market_data/providers/narrative_source_gateway.py`
- `scripts/run_narrative_source_gateway_probe.py`
- `scripts/run_fresh_narrative_digest.py`
- `scripts/run_narrative_candidate_inbox.py`
- `scripts/run_narrative_source_coverage_gap_report.py`
- `scripts/report_data_capabilities.py`
- `src/product_shell/source_quality.py`
- `src/scanners/fresh_narrative_digest.py`
- `src/scanners/narrative_source_coverage_gap.py`
- `tests/test_narrative_source_gateway_consumer.py`
- `tests/test_fresh_narrative_digest.py`
- `tests/test_narrative_source_coverage_gap.py`
- `tests/test_product_shell_source_quality.py`
- `outputs/fresh_narrative_digest/current/fresh_narrative_digest.json`
- `outputs/fresh_narrative_digest/current/fresh_narrative_digest.html`
- `docs/exec-plans/active/fni-gateway-source-events.md`
- `docs/exec-plans/active/index.md`
- `docs/memory/current-brief.md`
- `docs/product/open-source-first-narrative-data-strategy-2026-06-04.html`

## Implementation Summary

FNI now defaults to `GET /api/v1/market-data/narrative/source-events` for narrative source-event probing and consumption. The client builds unified query parameters, preserves Gateway structured degradation, and supports the M20 source kinds `official_filings`, `official_disclosures`, `official_sources`, `news_context`, `open_news_index`, `industry_media`, and `social_heat`.

FNI also now emits the downstream M20 consumer artifacts required by the FNI Linear issues: source-quality dashboard rows for every source kind, fresh digest missing/degraded input diagnostics, candidate inbox grouping without trust promotion, and a Gateway backlog coverage gap report.

## Commands Run

- `python -m pytest tests/test_narrative_source_gateway_consumer.py -q`
- `python scripts/run_narrative_source_gateway_probe.py --base-url http://127.0.0.1:8700 --timeout-seconds 45 --limit 5 --output-dir outputs/narrative_source_gateway_probe/current`
- `python scripts/run_fresh_narrative_digest.py --input outputs/narrative_source_gateway_probe/current/narrative_source_gateway_probe.json --output-dir outputs/fresh_narrative_digest/current --window-start 2026-06-05T00:00:00+00:00 --window-end 2026-06-05T23:59:59+00:00`
- `python scripts/run_narrative_candidate_inbox.py --input outputs/narrative_source_gateway_probe/current/narrative_source_gateway_probe.json --output-dir outputs/narrative_candidate_inbox/current`
- `python scripts/run_narrative_source_coverage_gap_report.py --input outputs/narrative_source_gateway_probe/current/narrative_source_gateway_probe.json --output-dir outputs/narrative_source_coverage_gap/current`
- `python -m pytest`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`

## Test Results

- Targeted narrative source consumer tests: 7 passed.
- M20 report/source-quality target tests: 21 passed.
- Wider product-shell/source-event target tests: 43 passed.
- Full pytest: 684 passed, 1 skipped.
- Coverage run: 684 passed, 1 skipped; total coverage 84%.
- Ruff: passed.
- Compileall: passed.
- Live Gateway probe: exit 0; 7 source kinds, 0 failed kinds, 6 rows.
- Consumer artifacts: fresh digest degraded with 2 digest items; candidate inbox degraded with 2 candidates; coverage gap report degraded with 2 working, 3 missing, 2 degraded, and 1 unsupported source.

## Known Risks And Assumptions

- `open_news_index` can degrade from upstream timeout/rate-limit; FNI treats Gateway's structured degraded response as non-fatal.
- `social_heat` is intentionally disabled by default and appears as structured degraded.
- Legacy per-kind POST routes remain documented for compatibility, but FNI default probing uses the unified route.
- The clean PR branch is based on `origin/main` and contains only the FNI Gateway source-events work.

## Suggested Quality Checks

- Review the unified-route query construction and degradation semantics in `src/market_data/providers/narrative_source_gateway.py`.
- Confirm product expectations for whether `official_sources` should group with official disclosures/policy or receive a separate source-quality group in a later UI slice.
- Review the source-kind trust boundary in `src/scanners/fresh_narrative_digest.py`: only official Gateway source kinds can carry `trusted_fact`; open news/industry media remain `context_only`, and social heat remains `heat_signal_only`.
