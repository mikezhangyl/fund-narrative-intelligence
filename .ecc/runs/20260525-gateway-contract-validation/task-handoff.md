# Task Handoff

## Goal

Close the next five V0 data-source infrastructure steps: gateway contract,
gateway conformance validation, local gateway URL routing, controlled 100-symbol
stress validation, and AkShare endpoint isolation.

## Implementation Summary

- Added `config/market_data_gateway_contract.yaml`, a machine-readable multi-source gateway contract covering Tushare, AkShare, EastMoney, and gateway-owned `cyq_chips`.
- Added `src/market_data/gateway_contract.py` and `scripts/validate_market_data_gateway_contract.py` for contract loading and local gateway conformance checks.
- Extended gateway conformance checks with `--mode tushare-facade` for the currently documented `POST /tushare` gateway surface, while keeping normalized REST validation as the default.
- Added `--mode all` so a gateway can validate the normalized surface and the Tushare facade in one acceptance run once both are live.
- Added `minimum_rows` to gateway response contracts and conformance checks so empty success payloads are treated as completeness failures for available endpoints.
- Added `src/market_data/providers/local_gateway.py` and wired it into `ConsolidatedMarketDataSource` as an optional first-choice provider when `MARKET_DATA_GATEWAY_URL` is configured.
- Expanded runtime config reporting to show gateway route configuration and provider-level gateway readiness.
- Added partial-safe sector scan execution and `scripts/run_sector_scan.py`, so AkShare sector failures or empty sector payloads are recorded without aborting the scan.
- Tightened stress probes so empty sector rows count as a completeness failure instead of a completed sector scan.
- Ran controlled 100-symbol stress validation using stock metadata, capped at 100 symbols and batch size 50.
- Updated README with the gateway conformance, runtime, sector scan, stress, and reliability commands.
- Updated `docs/memory/current-brief.md` with the document-driven FNI/gateway coordination rule and the two current gateway consumption surfaces.
- Updated `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/fni-upstream-change-request-2026-05-25.md` so the gateway project has an explicit FNI-facing facade acceptance command.

## Files Changed

- `README.md`
- `config/data_sources.yaml`
- `config/market_data_gateway_contract.yaml`
- `docs/memory/current-brief.md`
- `src/market_data/gateway_contract.py`
- `src/market_data/providers/local_gateway.py`
- `src/market_data/runtime_config.py`
- `src/market_data/source_layer.py`
- `src/market_data/stress.py`
- `src/scanners/sector_scanner.py`
- `src/scanners/__init__.py`
- `scripts/validate_market_data_gateway_contract.py`
- `scripts/report_market_data_runtime.py`
- `scripts/build_market_data_reliability_report.py`
- `scripts/run_sector_scan.py`
- `tests/test_market_data_gateway_contract.py`
- `tests/test_local_gateway_provider.py`
- `tests/test_market_data_runtime_config.py`
- `tests/test_market_data_source_layer.py`
- `tests/test_market_data_scanners.py`
- `tests/test_market_data_stress.py`
- `tests/test_sector_scan_script.py`
- `tests/test_market_data_reliability_report.py`
- `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/fni-upstream-change-request-2026-05-25.md`

## Commands Run

- `python -m ruff check .`
- `python -m ruff check src/market_data/gateway_contract.py scripts/validate_market_data_gateway_contract.py src/scanners/sector_scanner.py src/market_data/stress.py tests/test_market_data_gateway_contract.py tests/test_market_data_scanners.py tests/test_market_data_stress.py`
- `python -m ruff check scripts/validate_market_data_gateway_contract.py tests/test_market_data_gateway_contract.py`
- `python -m compileall -q src tests scripts`
- `git diff --check`
- `python -m pytest tests/test_market_data_gateway_contract.py tests/test_local_gateway_provider.py tests/test_market_data_runtime_config.py -q`
- `python -m pytest tests/test_market_data_gateway_contract.py tests/test_market_data_scanners.py tests/test_market_data_stress.py tests/test_market_data_stress_script.py tests/test_sector_scan_script.py -q`
- `python scripts/validate_market_data_gateway_contract.py --help`
- `python scripts/validate_market_data_gateway_contract.py --base-url http://127.0.0.1:8700 --mode tushare-facade --endpoint-id tushare_trade_cal --endpoint-id tushare_daily --format markdown`
- `python scripts/validate_market_data_gateway_contract.py --base-url http://127.0.0.1:8700 --mode all --format markdown --output outputs/data_capabilities/gateway_conformance_2026-05-25.md`
- `python scripts/validate_market_data_gateway_contract.py --base-url http://127.0.0.1:8700 --mode all --format json --output outputs/data_capabilities/gateway_conformance_2026-05-25.json`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/report_market_data_runtime.py --format markdown --output outputs/data_capabilities/market_data_runtime_gateway_2026-05-25.md`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/report_market_data_runtime.py --format json --output outputs/data_capabilities/market_data_runtime_gateway_2026-05-25.json`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/run_sector_scan.py --trade-date 2026-05-22 --output-dir outputs/sector_scan/2026-05-25-gateway`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/run_market_data_stress.py --use-stock-metadata --max-symbols 100 --batch-size 50 --start-date 2026-05-18 --end-date 2026-05-22 --trade-date 2026-05-22 --output-dir outputs/market_data_stress/2026-05-25-gateway-100`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/run_market_data_stress.py --use-stock-metadata --max-symbols 500 --batch-size 100 --start-date 2026-05-18 --end-date 2026-05-22 --trade-date 2026-05-22 --output-dir outputs/market_data_stress/2026-05-25-gateway-500` (interrupted after more than 3 minutes with no report output)
- `python scripts/build_market_data_reliability_report.py --runtime outputs/data_capabilities/market_data_runtime_gateway_2026-05-25.json --stress outputs/market_data_stress/2026-05-25-gateway-100/stress_report.json --format markdown --output outputs/data_capabilities/market_data_reliability_gateway_2026-05-25.md`
- `python scripts/build_market_data_reliability_report.py --runtime outputs/data_capabilities/market_data_runtime_gateway_2026-05-25.json --stress outputs/market_data_stress/2026-05-25-gateway-100/stress_report.json --format json --output outputs/data_capabilities/market_data_reliability_gateway_2026-05-25.json`
- `python scripts/validate_market_data_gateway_contract.py --base-url http://127.0.0.1:8700 --mode all --format markdown --output outputs/data_capabilities/gateway_conformance_2026-05-25-postfix.md`
- `python scripts/validate_market_data_gateway_contract.py --base-url http://127.0.0.1:8700 --mode all --format json --output outputs/data_capabilities/gateway_conformance_2026-05-25-postfix.json`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/report_market_data_runtime.py --format markdown --output outputs/data_capabilities/market_data_runtime_gateway_2026-05-25-postfix.md`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/report_market_data_runtime.py --format json --output outputs/data_capabilities/market_data_runtime_gateway_2026-05-25-postfix.json`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/run_sector_scan.py --trade-date 2026-05-22 --output-dir outputs/sector_scan/2026-05-25-gateway-postfix`
- `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700 python scripts/run_market_data_stress.py --use-stock-metadata --max-symbols 100 --batch-size 50 --start-date 2026-05-18 --end-date 2026-05-22 --trade-date 2026-05-22 --output-dir outputs/market_data_stress/2026-05-25-gateway-postfix-100`
- Gateway strict 500-symbol probe using `LocalGatewayMarketDataProvider` only, `max_symbols=500`, `batch_size=100`, outer timeout `180s`, output `outputs/market_data_stress/2026-05-25-gateway-strict-postfix-500`.
- FNI consolidated 500-symbol probe with outer timeout `240s`, output `outputs/market_data_stress/2026-05-25-gateway-postfix-500` if completed; this timed out and wrote no report.
- `python scripts/build_market_data_reliability_report.py --runtime outputs/data_capabilities/market_data_runtime_gateway_2026-05-25-postfix.json --stress outputs/market_data_stress/2026-05-25-gateway-postfix-100/stress_report.json --format markdown --output outputs/data_capabilities/market_data_reliability_gateway_2026-05-25-postfix.md`
- `python scripts/build_market_data_reliability_report.py --runtime outputs/data_capabilities/market_data_runtime_gateway_2026-05-25-postfix.json --stress outputs/market_data_stress/2026-05-25-gateway-postfix-100/stress_report.json --format json --output outputs/data_capabilities/market_data_reliability_gateway_2026-05-25-postfix.json`
- `python -m coverage run -m pytest -q`
- `python -m coverage report`
- `python scripts/run_market_data_stress.py --use-stock-metadata --max-symbols 100 --batch-size 50 --start-date 2026-05-18 --end-date 2026-05-22 --trade-date 2026-05-22 --output-dir outputs/market_data_stress/2026-05-25-controlled-100`
- `python scripts/run_sector_scan.py --trade-date 2026-05-22 --output-dir outputs/sector_scan/2026-05-25-controlled`
- `python scripts/report_market_data_runtime.py --format markdown --output outputs/data_capabilities/market_data_runtime_report.md`
- `python scripts/report_market_data_runtime.py --format json --output outputs/data_capabilities/market_data_runtime_report.json`
- `python scripts/build_market_data_reliability_report.py --stress outputs/market_data_stress/2026-05-25-controlled-100/stress_report.json --format markdown --output outputs/data_capabilities/market_data_reliability_report.md`
- `python scripts/build_market_data_reliability_report.py --stress outputs/market_data_stress/2026-05-25-controlled-100/stress_report.json --format json --output outputs/data_capabilities/market_data_reliability_report.json`

## Test Results

- Targeted gateway/runtime tests: `14 passed`.
- Targeted gateway/scanner/stress tests: `24 passed`.
- Full pytest suite: `416 passed, 1 skipped`.
- Coverage: `82%` total, above the configured `80%` gate.
- Ruff: passed.
- Compileall: passed.
- Diff whitespace check: passed.

## Live Evidence

- Local gateway conformance while service was healthy: `--mode tushare-facade` passed `5/5`; `--mode all` passed `11/13`.
- Normalized Tushare routes and EastMoney quote returned rows through gateway. AkShare sector concepts and limit-up/down returned `0` rows and now fail conformance via `minimum_rows`.
- Runtime report with `MARKET_DATA_GATEWAY_URL=http://127.0.0.1:8700`: gateway configured `True`; Tushare URL kind `local_gateway`.
- Gateway 100-symbol stress: `completed_with_failures`; historical and daily probes succeeded with `495` historical rows and `99` daily rows from `100` symbols; sector probe recorded `sector_data: returned no rows`.
- Gateway sector scan: `partial`; sector rows `0`, ETF rows `2`, failure `sector endpoint returned no rows`.
- Gateway 500-symbol stress attempt with batch size `100` did not write a report after more than three minutes and was interrupted from the FNI side. After interruption, small follow-up checks against `POST /tushare` `trade_cal` and normalized `stock-basic` timed out, suggesting the gateway service remained alive but was blocked by long-running work.
- Post-fix gateway conformance after upstream commit `64fa1e8`: `13/13` passed.
- Post-fix gateway sector scan: `completed`, `100` sector rows and `2` ETF rows.
- Post-fix gateway 100-symbol stress: `completed`, `0` failures, `696` rows.
- Post-fix FNI consolidated 500-symbol stress with batch size `100`: exceeded outer `240s` guard and wrote no report.
- Post-fix gateway-strict 500-symbol stress with batch size `100`: completed with failures; `12` requests, `696` rows, `8` failures. The failures were `504` responses from normalized Tushare daily routes: `4` historical daily batches and `4` incremental daily batches. Sector probe passed with `102` rows.
- After the strict 500-symbol run, `/api/health`, `/tushare` `trade_cal`, and normalized `stock-basic` passed, so service liveness recovered better than before. The remaining gap is large daily-scan throughput/timeout.
- Clean rerun after the new gateway service start: health `200`; conformance `13/13`; sector scan `completed` with `100` sector rows and `2` ETF rows; 100-symbol stress `completed` with `0` failures and `696` rows.
- Clean rerun gateway-strict 500-symbol stress: `completed_with_failures`; `12` requests, `995` rows, `5` failures. Historical had `4` HTTP `504` failures; daily had `1` HTTP `504` failure; sector had `0` failures. Gateway health was still `200` afterward.

## Known Risks And Assumptions

- `MARKET_DATA_GATEWAY_URL` is intentionally optional. No behavior changes unless it is configured or a gateway provider is injected.
- `TUSHARE_API_URL=http://127.0.0.1:8700/tushare` remains the low-friction compatibility path for existing Tushare-style callers while normalized gateway routes mature.
- AkShare sector concepts and limit up/down currently need gateway-side completeness fixes; empty success payloads are no longer accepted by FNI conformance.
- The gateway may need a restart after the interrupted 500-symbol probe before further live validation.

## Suggested Quality Checks

- Restart or unblock the gateway service, then rerun `python scripts/validate_market_data_gateway_contract.py --base-url http://localhost:8700 --mode tushare-facade`.
- Fix gateway-side AkShare sector/limit completeness, then rerun `python scripts/validate_market_data_gateway_contract.py --base-url http://localhost:8700 --mode all`.
- Keep 100-symbol gateway stress as the passing V0 baseline for now.
- Treat 500-symbol daily scan as a gateway reliability target until normalized Tushare daily can handle 500 symbols over a 5-trading-day window without HTTP `504`, or return a deterministic accepted/partial result.
- Keep sector scan failures as degraded evidence until AkShare/EastMoney concept endpoints are stable through gateway cache or replacement endpoints.
