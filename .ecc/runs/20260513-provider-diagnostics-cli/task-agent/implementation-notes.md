# Implementation Notes

## Summary

Added a provider diagnostics CLI path that prints provider foundation metadata without generating report artifacts.

## Changes

- Added `inspect_provider_foundation()` in `src/orchestrator.py`.
- Added `--provider-diagnostics` to `src/main.py`.
- Added subprocess and direct unit tests for diagnostics behavior.
- Documented the command in README, V1 spec, project memory, ADRs, and the active execution plan.

## Result

Developers can now run `python -m src.main --fund-code 000001 --provider-diagnostics` to see which provider layers are mock, partial, or degraded before generating a report.
