# Task Handoff

## Goal

Complete MIK-239 by generating a Tushare news permission/live-smoke feasibility
artifact and exposing it in the product shell.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds `tushare-news-permission-smoke-v1`, emitted as JSON and Chinese
HTML under `outputs/tushare_news_permission_smoke/current/`. The CLI probes
candidate `src` values through `ConsolidatedMarketDataSource.fetch_news_briefs`,
which preserves the existing FNI -> stock-data-gateway source boundary.

The current live run used `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700` and
checked `sina`, `wallstreetcn`, `10jqka`, `eastmoney`, `yicai`, and `cls` over
`2026-06-01 00:00:00` to `2026-06-02 23:59:59`. The result is `Blocked` because
gateway port 8700 refused the connection. This is not evidence of Tushare paid
permission failure; it proves the gateway boundary was unreachable for the
smoke. The report records this distinction explicitly.

## Commands Run

- `uv run pytest tests/test_tushare_news_permission_smoke.py -q`
- `uv run pytest tests/test_tushare_news_permission_smoke.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `curl -sS http://127.0.0.1:8700/health`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 uv run python scripts/run_tushare_news_permission_smoke.py --start-datetime "2026-06-01 00:00:00" --end-datetime "2026-06-02 23:59:59" --limit 5 --output-dir outputs/tushare_news_permission_smoke/current`
- `uv run ruff check .`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `667 passed, 1 skipped`.

## Decision Log

- Kept provider access gateway-owned because previous architecture decisions and R13 matrix say FNI must not add direct Tushare/news integrations.
- Classified the live result as `Blocked`, not `Paid Permission Required`, because gateway 8700 returned connection refused before a Tushare permission check could happen.
- Added product shell route `/sources/tushare-news-smoke` so the smoke is visible as a real artifact, not only a script output.
- Added secret redaction tests and scanner redaction because provider errors may include token-like values.

## Known Risks And Assumptions

This run does not prove Tushare news permission status. It proves the current
FNI-side smoke cannot reach the gateway boundary. A follow-up run with
stock-data-gateway running on 8700 is required to distinguish Dev-Ready from
Paid Permission Required.

## Suggested Quality Checks

- Start stock-data-gateway on 8700 and rerun the same CLI.
- If provider errors show `PROVIDER_PERMISSION_REQUIRED`, treat Tushare news as
  Paid Permission Required before assigning gateway integration work.
