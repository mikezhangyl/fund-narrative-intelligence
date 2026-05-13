# Provider Adapter Foundation Execution Plan

## Purpose

Make the provider layer ready for the first real fund-holdings adapter while keeping mock fixtures as the deterministic baseline.

## Scope

- Provider protocol.
- Real-provider adapter candidate for fund holdings.
- Fallback semantics.
- Tests around provider selection and normalization.

## Acceptance

- Mock mode behavior remains unchanged.
- Real mode either returns validated real holdings or records a clear fallback/degradation event.
- The pipeline still generates required artifacts.

## Status

Implemented and locally verified.

Provider modes:

- `mock`: deterministic local fixtures.
- `real`: compatibility fallback to mock.
- `eastmoney`: no-key Eastmoney/Tiantian Fund fund-holdings adapter.

Smoke result:

- `python -m src.main --fund-code 161725 --provider-mode eastmoney` generated all four artifacts with primary narrative `Premium Baijiu Consumption` and stage `diverging`.

## Run Record

- `.ecc/runs/20260513-provider-adapter-foundation/`
