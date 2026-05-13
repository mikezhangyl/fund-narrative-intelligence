# Real Fund Scoring Calibration Execution Plan

## Purpose

Make the six-fund Eastmoney smoke set produce a more differentiated V1 stage distribution instead of classifying every primary narrative as `diverging`.

## Scope

- Inspect current smoke scoring and signal drivers.
- Add tests for expected stage differentiation across the fixed smoke set.
- Adjust local signal fixtures and, only if needed, deterministic stage rules.
- Keep the real-provider boundary unchanged: holdings are live, registry/evidence/signals remain local V1 fixtures.
- Update docs and memory with calibrated smoke expectations.

## Acceptance

- `python -m src.main --run-real-smoke` passes.
- The smoke set includes at least three distinct lifecycle stages.
- Mock fixture scenarios keep their expected stages.
- Full quality gates pass.

## Status

Implemented and locally verified.

Latest calibrated smoke result:

- `strengthening`: `320007` Semiconductor Capex Cycle, `001475` Defense Aerospace.
- `diverging`: `161725` Premium Baijiu Consumption, `003096` Healthcare Innovation.
- `weakening`: `003834` New Energy Equipment, `000991` Real Estate Stabilization.

## Run Record

- `.ecc/runs/20260513-real-fund-scoring-calibration/`
