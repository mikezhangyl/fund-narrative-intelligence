# Real Smoke Precision Summary Execution Plan

## Purpose

Make the fixed real-smoke summary a registry-curation workbench by aggregating mapping precision flags across funds.

## Scope

- Include `mapping_precision_flags` and counts in each real-smoke fund result.
- Render a `Mapping Precision Flags` section in `real_fund_smoke_summary.md`.
- Keep existing mapping gap and multi-mapped holding diagnostics.

## Non-Goals

- Resolving the remaining ambiguous flags.
- Changing registry terms or scoring rules.

## Acceptance

- Unit tests cover summary JSON and Markdown precision flag output.
- Real smoke still passes and shows remaining precision work items.
- Full quality gates and live smoke commands pass.

## Run Record

- `.ecc/runs/20260514-real-smoke-precision-summary/`
