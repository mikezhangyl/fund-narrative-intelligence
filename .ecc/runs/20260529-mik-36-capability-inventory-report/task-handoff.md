# Task Handoff

## Goal

Complete Linear MIK-36 by upgrading the market-data capability report from a
flat registry dump into a grouped inventory with machine-readable JSON, Chinese
HTML, and auxiliary Markdown outputs.

## Files Changed

- `scripts/report_data_capabilities.py`
- `tests/test_market_data_capabilities.py`
- `docs/product/README.md`
- `docs/memory/current-brief.md`

Generated verification outputs:

- `outputs/data_capabilities/2026-05-29-inventory.json`
- `outputs/data_capabilities/2026-05-29-inventory.html`
- `outputs/data_capabilities/2026-05-29-inventory.md`

## Implementation Summary

Added `build_inventory_report()` with grouped `dataset_rows`,
`inventory_groups`, explicit `status_labels`, derived last-smoke status,
degradation behavior, and a narrative service row. The CLI now supports
`--format html` in addition to JSON and Markdown. The generated HTML is
Chinese, includes source/gateway/degradation fields, and keeps status labels
visible for Can-Do, unstable, blocked, and future capabilities.

## Commands Run

- `uv run pytest tests/test_market_data_capabilities.py -q`
- `uv run python scripts/report_data_capabilities.py --format json --output outputs/data_capabilities/2026-05-29-inventory.json`
- `uv run python scripts/report_data_capabilities.py --format markdown --output outputs/data_capabilities/2026-05-29-inventory.md`
- `uv run python scripts/report_data_capabilities.py --format html --output outputs/data_capabilities/2026-05-29-inventory.html`
- `uv run pytest tests/test_market_data_capabilities.py tests/test_market_data_gateway_contract.py tests/test_market_data_reliability_report.py -q`
- `uv run --extra dev ruff check scripts/report_data_capabilities.py tests/test_market_data_capabilities.py`
- `uv run python -m compileall -q src tests scripts`
- `git diff --check`

## Test Results

RED:

- Tests failed because `build_inventory_report` did not exist.
- A follow-up RED check caught `etf_spot_ranking` falling into the fallback
  `other` group.

GREEN:

- `tests/test_market_data_capabilities.py`: 9 passed.
- Related market-data/report tests: 20 passed.
- `ruff check`: passed.
- `compileall`: passed.
- `git diff --check`: passed.

## Known Risks And Assumptions

- Last-smoke status is derived from the capability registry and documented smoke
  paths. This slice does not run live gateway probes.
- Generated files under `outputs/data_capabilities/` are verification artifacts
  and are ignored by Git; the run manifest records their checksums.

## Suggested Quality Checks

- Re-run the inventory script for all three formats.
- Inspect the HTML output when changing inventory grouping or styling.
