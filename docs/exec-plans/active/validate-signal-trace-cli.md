# Validate Signal Trace CLI

## Goal

Add a direct CLI command to validate a generated signal trace artifact without
running a fund report.

## Scope

- Add `python -m src.main --validate-signal-trace path/to/fund_000001_signal_trace.json`.
- Reuse the shared signal trace artifact validator.
- Cover success and malformed artifact cases in tests.
- Document the command in product and project memory.

## Non-Goals

- No changes to signal trace schema.
- No report or web UI rendering.

## Acceptance

- CLI prints a success message and path for a valid signal trace artifact.
- CLI exits with parser error for malformed signal trace artifacts.
- Standard tests and V1 acceptance remain green.
