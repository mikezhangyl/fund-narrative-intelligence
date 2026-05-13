# Task Handoff

## Goal

Expand V1 from one live Eastmoney-backed fund check to a repeatable multi-fund real-holdings smoke set.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

- Added `--run-real-smoke` CLI support.
- Added `src/real_fund_smoke.py` with a fixed six-fund Eastmoney smoke set.
- Added summary JSON and Markdown artifacts for smoke results.
- Added per-fund failure isolation so summary artifacts are still generated when one fund fails.
- Broadened fixtures for healthcare, new energy, defense, and real estate sector narratives.
- Updated docs and memory files with smoke command, smoke set, and latest result.

## Commands Run

See `task-agent/commands.jsonl`.

## Test Results

Full regression passed: `31 passed in 0.36s`.

Real smoke passed for six funds:

- `161725`: Premium Baijiu Consumption / `diverging` / 100% coverage.
- `320007`: Semiconductor Capex Cycle / `diverging` / 95% coverage.
- `003096`: Healthcare Innovation / `diverging` / 100% coverage.
- `003834`: New Energy Equipment / `diverging` / 94% coverage.
- `001475`: Defense Aerospace / `diverging` / 88% coverage.
- `000991`: Real Estate Stabilization / `diverging` / 78% coverage.

## Known Risks And Assumptions

- Eastmoney availability is external and not guaranteed.
- Only holdings are real-provider-backed; narrative registry, evidence, and signals remain local fixtures.
- Sector fallback mapping is intended for smoke coverage, not final semantic precision.

## Suggested Quality Checks

- Re-run `python -m src.main --run-real-smoke` after any provider, registry, or mapping change.
- Inspect `outputs/real_fund_smoke_summary.md` and per-fund HTML reports before treating new sector coverage as product-ready.
