# Real Smoke Gap Mapping Rules Execution Plan

## Purpose

Resolve the concrete real-smoke mapping gaps exposed by the Eastmoney smoke summary.

## Scope

- Add conservative registry terms for current unmapped live holdings.
- Keep the mapping algorithm unchanged.
- Avoid broad industry terms where they would over-map unrelated companies.
- Verify the six-fund real smoke set reaches full mapping coverage without changing expected primary narratives or stages.

## Acceptance

- Current mapping-gap holdings map to intended narratives in unit tests.
- `python -m src.main --run-real-smoke` passes with 100% coverage for all six real smoke funds.
- Full quality gates pass.

## Status

Implemented and locally verified.

Latest smoke result:

- `161725`: Premium Baijiu Consumption / `diverging` / 100% coverage.
- `320007`: Semiconductor Capex Cycle / `strengthening` / 100% coverage.
- `003096`: Healthcare Innovation / `diverging` / 100% coverage.
- `003834`: New Energy Equipment / `weakening` / 100% coverage.
- `001475`: Defense Aerospace / `strengthening` / 100% coverage.
- `000991`: Real Estate Stabilization / `weakening` / 100% coverage.

## Run Record

- `.ecc/runs/20260513-real-smoke-gap-mapping-rules/`
