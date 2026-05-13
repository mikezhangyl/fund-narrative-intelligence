# Real Fund Expansion Execution Plan

## Purpose

Validate V1 against a small set of live Eastmoney fund-holdings scenarios across multiple sectors.

## Scope

- Real-fund smoke set.
- Smoke summary artifacts.
- Registry and mapping broadening.

## Acceptance

- Smoke command generates reports for the selected real funds.
- Smoke summary records mapping coverage, primary narrative, stage, and concrete unmapped holding details.
- Smoke summary remains writable when an individual real-fund run fails.
- Existing mock and Eastmoney single-fund commands remain compatible.

## Status

Implemented and locally verified.

Latest smoke result:

- `161725`: Premium Baijiu Consumption / `diverging` / 100% coverage.
- `320007`: Semiconductor Capex Cycle / `strengthening` / 95% coverage.
- `003096`: Healthcare Innovation / `diverging` / 100% coverage.
- `003834`: New Energy Equipment / `weakening` / 94% coverage.
- `001475`: Defense Aerospace / `strengthening` / 88% coverage.
- `000991`: Real Estate Stabilization / `weakening` / 78% coverage.

## Run Record

- `.ecc/runs/20260513-real-fund-expansion/`
