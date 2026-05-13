# V1 Multi-Fixture Scenarios Execution Plan

## Purpose

Verify the V1 pipeline works across multiple fund scenarios, not only the initial `000001` happy path.

## Scope

- Add more mock fund fixtures.
- Add batch command support.
- Validate different primary narrative stages across mock funds.

## Acceptance

- `python -m src.main --list-fixtures` lists at least three funds.
- `python -m src.main --run-all-fixtures --output-dir <dir>` generates four artifacts for every listed fund.
- `python -m src.main --fund-code 000001` remains compatible.

## Status

Implemented and locally verified.

Scenario coverage:

- `000001`: AI Infrastructure / `strengthening`
- `000002`: AI Power Demand / `crowded`
- `000003`: EV Price War / `dead`

## Run Record

- `.ecc/runs/20260513-multi-fixture-scenarios/`
