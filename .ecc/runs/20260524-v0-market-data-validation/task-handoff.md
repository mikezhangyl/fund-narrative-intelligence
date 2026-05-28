# Task Handoff

## Goal

Build the V0 market data source validation infrastructure: stable ingestion
adapters, cache/logging/fallback support, deterministic scanners, stress-test
measurement, and validation-matrix helpers.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

Added `src/market_data` with provider protocols, schemas, filesystem cache,
JSONL request logging, retry/pacing runtime, Tushare and AkShare V0 adapters,
fallback routing, validation records, and stress-test measurement. The V0
Tushare/AkShare adapters are thin extensions over the existing project provider
surface: Tushare reuses `src.providers.tushare_market.TushareMarketDataProvider`
for `.local.env` token loading and latest quote access, and AkShare reuses
`src.providers.akshare_market.AkshareMarketDataProvider` for client loading and
latest quote access. Added `ConsolidatedMarketDataSource` as the single V0
interface for latest quotes, daily bars, index bars, ETF data, sector data,
limit-up/down stats, provider health, and endpoint-level live validation. Added
`src/scanners` breadth and sector scanners. Added optional storage adapters for
Parquet with CSV fallback and PostgreSQL driver/env detection. Added
`config/data_sources.yaml` to document the V0 endpoint surface and explicit
exclusions.
Added `scripts/run_market_data_live_validation.py` as a repeatable low-volume
probe runner that emits JSON and Markdown reports without exposing secrets. The
runner disables local market-data cache so reported latencies reflect live
requests, and records runtime Python/AkShare versions for version-sensitive
AkShare probes.
Pinned `akshare==1.18.63` under the `market-data` optional dependency group in
`pyproject.toml` and upgraded the current environment to the same version.
Extended the probe runner with `--repeat` and `--interval-seconds`, plus an
endpoint status matrix that classifies endpoints as `primary`, `fallback`,
`unstable`, or `disabled`.

## Commands Run

- `python -m pytest tests/test_market_data_cache.py tests/test_market_data_v0_providers.py tests/test_market_data_scanners.py tests/test_market_data_stress.py -q`
- `python -m pytest tests/test_market_data_cache.py tests/test_market_data_v0_providers.py tests/test_market_data_scanners.py tests/test_market_data_stress.py tests/test_market_data_fallback_and_validation.py -q`
- `python -m pytest -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- Consolidated live validation smoke with one stock, one index, and one ETF.
- `python scripts/run_market_data_live_validation.py` after disabling local cache.
- `python -m pip install 'akshare==1.18.63'`
- `python scripts/run_market_data_live_validation.py` after formal environment
  upgrade.
- `python scripts/run_market_data_live_validation.py --repeat 2 --interval-seconds 1`

## Test Results

- Full pytest after consolidated source layer: 369 passed, 1 skipped.
- Full pytest after repeat-window diagnostics: 371 passed, 1 skipped.
- Ruff: all checks passed.
- Compileall: passed.
- Coverage: 82% total.
- Live validation smoke: 5 of 6 checks available. AkShare concept sector endpoint
  failed due an upstream EastMoney connection/proxy disconnect, while AkShare
  limit-up/down stats passed.
- Low-volume no-cache endpoint probe: 7 of 10 checks available. EastMoney quote and
  Tushare stock_basic/daily/daily_basic/index_daily/fund_daily passed. AkShare
  stock_zh_a_hist, fund_etf_hist_em, and stock_board_concept_name_em failed
  with EastMoney push endpoint connection/proxy disconnects. AkShare
  limit-up/down stats passed.
- Temporary isolated AkShare 1.18.63 probe: sector_concepts recovered once
  with 486 rows but failed in the next two runs; stock_zh_a_hist and
  fund_etf_hist_em remained 0/3. Treat AkShare concept sectors as
  version-sensitive but still unstable in the current network window.
- Formal project environment upgraded to AkShare 1.18.63. Full pytest passed
  with 369 passed, 1 skipped. Post-upgrade live probe still showed Tushare and
  EastMoney quote available, AkShare limit-up/down available, and AkShare
  stock_zh_a_hist/fund_etf_hist_em/stock_board_concept_name_em failing in this
  network window.
- Repeat-window live validation produced 6 primary endpoints, 1 fallback
  endpoint, 0 unstable endpoints, and 3 disabled endpoints in the current
  two-window probe.

## Known Risks And Assumptions

Live Tushare and AkShare endpoint stability still needs credentialed/networked
runtime validation. `.local.env` exists and the existing `local_env` token path is
reused, but this handoff intentionally does not expose or duplicate secret values.
The code isolates endpoint calls, logs failures, and supports cache/fallback, but
this turn did not run live provider requests against external services.

## Suggested Quality Checks

Run credentialed V0 scans with a small A-share symbol sample first, then scale to
full historical and daily-update stress tests while inspecting
`data/logs/provider_requests.jsonl`.
