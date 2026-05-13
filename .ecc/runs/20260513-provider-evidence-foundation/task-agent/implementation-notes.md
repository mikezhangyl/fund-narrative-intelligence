# Implementation Notes

## Summary

Added provider foundation metadata and user-facing data source disclosure for mock, degraded, and mixed real/mock runs.

## Changes

- Added `src/providers/provenance.py` for per-layer provider provenance.
- Added `provider_foundation` to raw and scoring JSON.
- Switched scoring/report metadata to `provider_foundation.effective_data_quality`.
- Marked Eastmoney holdings plus fixture-backed registry, mappings, evidence, and signals as `partial`.
- Rendered `Data Source Notice` in Markdown and HTML reports.
- Added degradation-event rendering for fallback runs.
- Extended real-fund smoke summaries with `Data Quality` and `Notice` columns.
- Updated README, implementation spec, project memory, and ADRs.

## Result

Users opening generated reports can now see whether analysis is pure mock, fallback-to-mock, or mixed real/mock. The system no longer labels Eastmoney-holdings reports as fully `fresh` while the intelligence layers remain fixture-backed.
