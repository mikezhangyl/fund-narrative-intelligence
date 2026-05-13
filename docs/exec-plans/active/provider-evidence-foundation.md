# Provider Evidence Foundation Execution Plan

## Purpose

Separate provider provenance by data layer and make mock, degraded, or mixed provider usage visible to users in report output.

## Scope

- Add run-level provider foundation metadata.
- Track effective data quality separately from fund-holdings quality.
- Mark Eastmoney holdings plus fixture-backed intelligence layers as `partial`.
- Render `Data Source Notice` in Markdown and HTML reports.
- Extend real-fund smoke summaries with data quality and notice columns.
- Preserve mock and Eastmoney provider behavior.

## Acceptance

- Pure mock reports visibly state they use Mock fixtures.
- `real` mode fallback reports visibly show `provider_fallback`.
- Eastmoney holdings with fixture-backed registry, mappings, evidence, and signals are marked `partial`, not `fresh`.
- Full quality gates pass.

## Status

Implemented locally; final verification and run artifact closure pending.

## Run Record

- `.ecc/runs/20260513-provider-evidence-foundation/`
