# Task Handoff

## Goal

Implement a machine-readable market-data capability registry that records which
datasets each analysis capability requires, current acquisition status and
difficulty, primary/fallback source ownership, local gateway readiness, and
known validation gaps.

## Files Changed

- `config/data_capabilities.yaml`
- `src/market_data/capabilities.py`
- `src/market_data/providers/tushare.py`
- `src/market_data/source_layer.py`
- `scripts/report_data_capabilities.py`
- `scripts/run_market_data_live_validation.py`
- `tests/test_market_data_capabilities.py`
- `tests/test_market_data_live_validation_script.py`
- `tests/test_market_data_v0_providers.py`
- `tests/test_market_data_source_layer.py`
- `README.md`
- `pyproject.toml`
- `docs/memory/current-brief.md`
- `.ecc/memory/project/system-facts.md`

## Implementation Summary

- Added a two-layer capability registry: datasets and analysis capabilities.
- Added a typed loader/validator with summaries and live-probe annotation.
- Added analysis readiness evaluation so each scanner can distinguish blockers from unstable-but-runnable warnings.
- Added a Markdown/JSON report CLI for the registry.
- Linked live validation endpoint status matrix rows to registry metadata.
- Added V0 Tushare `trade_cal` support and exposed it through the consolidated source layer.
- Added a capability-driven breadth scan planner that resolves symbols, trade calendars, lookback windows, and daily-bar execution inputs through the consolidated data source.
- Added `scripts/run_breadth_scan.py` for controlled breadth scan plans/execution, with safe low-volume defaults and explicit opt-in for metadata-wide symbol universe expansion.
- Added `scripts/run_market_data_stress.py` for controlled historical, incremental daily, and sector-rotation stress probes.
- Normalized stress-test peak memory reporting to KB on macOS/Linux and preserved structured failure reasons in stress outputs.
- Added runtime wiring inspection for provider URL kind, cache/log paths, pacing/retry settings, and redacted token source.
- Added consolidated V0 reliability report generation across capability readiness, runtime wiring, live validation, and controlled stress evidence.
- Recorded the long-term data-source platform objective in startup/project memory.
- Documented the registry command in the README.

## Commands Run

- `python -m pytest tests/test_market_data_capabilities.py -q`
- `python -m pytest tests/test_market_data_live_validation_script.py tests/test_market_data_capabilities.py -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m pytest -q`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python scripts/report_data_capabilities.py --format markdown --output outputs/data_capabilities/data_capability_report.md`
- `python scripts/report_data_capabilities.py --format json --output outputs/data_capabilities/data_capability_report.json`
- `python scripts/run_market_data_live_validation.py --trade-date 20260522 --stock-code 600519 --tushare-symbol 600519.SH --index-symbol 000001.SH --etf-symbol 510300.SH --repeat 1 --output-dir outputs/market_data_live_validation/2026-05-25-data-capability-registry`
- `python scripts/run_breadth_scan.py --end-date 2026-05-22 --lookback-trading-days 5 --plan-only --output-dir outputs/breadth_scan/2026-05-25-controlled-plan`
- `python scripts/run_breadth_scan.py --end-date 2026-05-22 --lookback-trading-days 5 --output-dir outputs/breadth_scan/2026-05-25-controlled-execution`
- `python scripts/run_market_data_stress.py --output-dir outputs/market_data_stress/2026-05-25-controlled-v0 --start-date 2026-05-18 --end-date 2026-05-22 --trade-date 2026-05-22 --batch-size 2`
- `python scripts/report_market_data_runtime.py --format markdown --output outputs/data_capabilities/market_data_runtime_report.md`
- `python scripts/report_market_data_runtime.py --format json --output outputs/data_capabilities/market_data_runtime_report.json`
- `python scripts/build_market_data_reliability_report.py --format markdown --output outputs/data_capabilities/market_data_reliability_report.md`
- `python scripts/build_market_data_reliability_report.py --format json --output outputs/data_capabilities/market_data_reliability_report.json`

## Test Results

- Targeted capability/live-validation/provider/scanner/stress/runtime/reliability tests: passed
- Full pytest suite: `399 passed, 1 skipped`
- Coverage: `82%` total, above the configured `80%` gate
- Ruff: passed
- Compileall: passed
- Live validation: `8/11` checks available; Tushare `trade_cal`, `daily`, `daily_basic`, `index_daily`, `fund_daily`, and `stock_basic` passed; AkShare history/ETF/concept endpoints failed in this network window; AkShare limit-up/down passed.
- Controlled breadth scan: `completed` for 3 symbols over 5 trading days, 15 daily-bar rows, via the consolidated data-source layer.
- Controlled stress probe: `completed_with_failures`; historical and daily probes succeeded, sector probe had `1` failure and `0` rows, with the AkShare/EastMoney proxy disconnect captured in `failure_reasons`.
- Runtime report: Tushare URL kind is `official_default`; token is configured from `.local.env`; cache/log paths exist.
- Reliability report: current V0 status is `degraded`, primarily due to AkShare/EastMoney sector/fallback instability and planned gateway-owned `cyq_chips`.

## Known Risks And Assumptions

- `trade_calendar` is now marked `available` and can be validated through Tushare `trade_cal`.
- `cyq_chips` is marked `gateway_owned`, because it should be implemented in the extracted local data gateway based on Cost-Basis-Trading work.
- AkShare sector concepts remain `unstable`; limit-up/down is available but not treated as primary infrastructure.
- `PyYAML==6.0.2` is now a runtime dependency for parsing the registry.

## Suggested Quality Checks

- Review that the dataset statuses reflect the latest live validation evidence before using them for release gating.
- When the local data gateway is ready, switch applicable Tushare entries from direct token API to gateway-backed source ownership.
- Expand `scripts/run_breadth_scan.py` from controlled symbols to larger symbol batches only after cache/gateway routing is available.
