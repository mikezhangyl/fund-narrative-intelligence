# Real Smoke CLI Precision Counts Execution Plan

## Purpose

Expose real-smoke mapping precision work directly in terminal output.

## Scope

- Print `precision_flags=<count>` for each fund in `--run-real-smoke` stdout.
- Keep existing status, primary narrative, stage, and coverage output.
- Preserve compatibility with summary dictionaries that do not yet include precision counts.

## Non-Goals

- Changing smoke pass/fail criteria.
- Resolving remaining precision flags.

## Acceptance

- CLI tests cover the new stdout field.
- Full quality gates and smoke commands pass.

## Run Record

- `.ecc/runs/20260514-real-smoke-cli-precision-counts/`
