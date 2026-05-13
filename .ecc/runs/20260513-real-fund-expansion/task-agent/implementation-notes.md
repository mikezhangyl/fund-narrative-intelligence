# Implementation Notes

## Summary

Expanded the real-provider validation path from a single Eastmoney fund run to a fixed six-fund smoke set with summary artifacts and per-fund failure isolation.

## Changes

- Added `src.real_fund_smoke.run_real_fund_smoke`.
- Added CLI support for `python -m src.main --run-real-smoke`.
- Added a fixed smoke set for baijiu consumption, semiconductor, healthcare, new energy, defense, and real estate scenarios.
- Broadened narrative registry, evidence, and signal fixtures enough for sector-level mapping and scoring.
- Added registry-term fallback mapping coverage for real holdings that lack exact fixture mappings.
- Added tests for smoke set shape, summary success/failure behavior, and runner failure isolation.
- Updated README, V1 implementation spec, project memory, and architecture decisions.

## Result

`python -m src.main --run-real-smoke` now writes `outputs/real_fund_smoke_summary.json` and `outputs/real_fund_smoke_summary.md`, while also generating standard per-fund raw, scoring, Markdown, and HTML artifacts.
