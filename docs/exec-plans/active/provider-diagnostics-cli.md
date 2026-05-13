# Provider Diagnostics CLI Execution Plan

## Purpose

Expose provider foundation metadata directly from the CLI without generating report artifacts.

## Scope

- Add `--provider-diagnostics`.
- Return provider foundation JSON for the selected fund and provider mode.
- Keep diagnostics read-only with respect to output artifacts.
- Show fallback events for `real` mode.
- Document the command.

## Acceptance

- `python -m src.main --fund-code 000001 --provider-diagnostics` prints JSON and writes no artifacts.
- `python -m src.main --fund-code 000001 --provider-mode real --provider-diagnostics` includes `provider_fallback`.
- Full quality gates pass.

## Status

Implemented locally; final run artifact closure pending.

## Run Record

- `.ecc/runs/20260513-provider-diagnostics-cli/`
