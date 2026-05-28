# Task Handoff

## Goal

Complete Linear MIK-45 by making the gateway-owned market-data boundary explicit
in FNI's capability registry, contract coverage checks, reporting surface, and
product documentation.

## Files Changed

- `config/data_capabilities.yaml`
- `src/market_data/capabilities.py`
- `scripts/report_data_capabilities.py`
- `tests/test_market_data_capabilities.py`
- `docs/product/market-data-gateway-boundary.md`
- `docs/product/README.md`

## Implementation Summary

Added an `ownership_policy` block to the capability registry, added
`gateway_contract_coverage()` to compare available gateway contract datasets
against the capability inventory, and filled missing contract datasets for ETF
spot ranking and news briefs. The capability report now renders the gateway
ownership boundary in Markdown and JSON. A product document records the
gateway-first external-source rule, dataset status meanings, disclosure
expectations, and Can-Do versus stable distinction.

## Commands Run

- `uv run pytest tests/test_market_data_capabilities.py -q`
- `uv run pytest tests/test_market_data_capabilities.py::test_data_capability_report_builds_markdown_and_json -q`
- `uv run pytest tests/test_market_data_capabilities.py tests/test_market_data_gateway_contract.py tests/test_daily_market_structure_report.py tests/test_fund_holding_exposure_report.py tests/test_fund_exposure_comparison_report.py tests/test_fund_narrative_exposure_matrix_report.py -q`
- `git diff --check`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260529-mik-45-gateway-boundary`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260529-mik-45-gateway-boundary --require-task-artifacts --require-quality-artifacts`
- `uv run python -m compileall -q src tests scripts`
- `uv run --extra dev ruff check .`
- `uv run --extra dev python -m coverage run -m pytest tests/test_market_data_capabilities.py tests/test_market_data_gateway_contract.py tests/test_daily_market_structure_report.py tests/test_fund_holding_exposure_report.py tests/test_fund_exposure_comparison_report.py tests/test_fund_narrative_exposure_matrix_report.py -q`

## Test Results

RED:

- `tests/test_market_data_capabilities.py` failed because
  `DataCapabilityRegistry.gateway_contract_coverage` and `ownership_policy`
  did not exist.
- The capability report test failed because Markdown did not render a gateway
  ownership boundary section.

GREEN:

- `tests/test_market_data_capabilities.py`: 7 passed.
- Related market-data/report tests: 32 passed.
- `git diff --check`: passed.
- `compileall`: passed.
- `ruff check`: passed after running with `--extra dev`.
- Coverage-backed related market-data/report test bundle: 32 passed.
- ECC run validation with required task and quality artifacts: passed.

## Known Risks And Assumptions

- This slice updates FNI's consumer-side boundary and inventory. It does not
  change gateway implementation behavior.
- The capability registry still distinguishes Can-Do availability from stable
  reliability; unstable datasets remain warnings, not blockers.

## Suggested Quality Checks

- Re-run the targeted market-data/report test bundle.
- Review whether future MIK-36 HTML inventory work should expose the ownership
  policy in Chinese reader-facing output.
