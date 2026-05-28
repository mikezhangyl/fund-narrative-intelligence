# Task Handoff

## Goal

Add FNI-side runnable Can-Do probes after the gateway exposes provider-neutral
market-data endpoints.

## Files Changed

- src/market_data/providers/local_gateway.py
- src/market_data/source_layer.py
- scripts/run_sector_scan.py
- scripts/run_etf_spot_probe.py
- scripts/run_limit_up_down_probe.py
- scripts/run_news_briefs_smoke.py
- tests/test_local_gateway_provider.py
- tests/test_market_data_source_layer.py
- tests/test_can_do_probe_scripts.py

## Implementation Summary

The local gateway provider now consumes the provider-neutral sector,
ETF spot, market limit-up/down, and news brief routes. The consolidated source
layer exposes ETF spot and news brief methods without adding direct provider
integrations. Three new probe commands write JSON and Markdown reports under
`outputs/` by default. The existing sector scan report now includes
`data_fetch_mode`, source, and degradation events.

## Commands Run

- `uv run pytest tests/test_local_gateway_provider.py tests/test_market_data_source_layer.py tests/test_can_do_probe_scripts.py`
- `uv run pytest tests/test_local_gateway_provider.py tests/test_market_data_source_layer.py tests/test_can_do_probe_scripts.py tests/test_sector_scan_script.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run python -m compileall -q src tests scripts`
- `uv run coverage run -m pytest -q`
- `uv run coverage report`
- `git diff --check`

## Test Results

- Targeted FNI tests: 20 passed.
- Full FNI test suite: 429 passed, 1 skipped.
- Coverage: 82%, above the 80% threshold.
- Ruff: passed.
- Compileall: passed.
- Diff whitespace: passed.

## Known Risks And Assumptions

- No live gateway smoke run was performed in this pass.
- The news smoke command relies on the gateway returning Tushare permission
  errors with a structured error code.
- The FNI worktree contains many unrelated dirty/untracked files; no unrelated
  cleanup was attempted.

## Suggested Quality Checks

- With the gateway running on `MARKET_DATA_GATEWAY_URL`, run the new probe
  scripts once against live providers and inspect generated reports.
