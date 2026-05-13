# V1 Hardening Execution Plan

## Purpose

Stabilize the mock-first V1 pipeline before adding real data providers.

## Scope

- Validate provider payload contracts.
- Return controlled pipeline errors for invalid fixtures and missing sample funds.
- Improve CLI usability with fixture discovery.
- Add docs for local usage and artifact inspection.

## Acceptance

- Full test suite passes.
- `python -m src.main --list-fixtures` lists available mock fund codes.
- `python -m src.main --fund-code 999999` fails with a clear controlled error.
- `python -m src.main --fund-code 000001` still produces the four required artifacts.

## Status

Implemented and locally verified.

## Run Record

- `.ecc/runs/20260513-v1-hardening/`
