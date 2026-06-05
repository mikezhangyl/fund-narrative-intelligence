# Implementation Notes

## Summary

FNI now consumes Gateway narrative source events through the unified provider-neutral route:

`GET /api/v1/market-data/narrative/source-events`

The FNI client no longer defaults to per-source POST routes for source-event probing. It supports the M20 source kinds `official_filings`, `official_disclosures`, `official_sources`, `news_context`, `open_news_index`, `industry_media`, and `social_heat`.

The FNI consumer/reporting layer now also covers the M20 downstream artifacts: source-quality rows for each Gateway source kind, fresh narrative digest input-gap diagnostics, candidate narrative inbox grouping, and a Gateway backlog coverage-gap report.

## Key Changes

- Added unified Gateway endpoint to `config/market_data_gateway_contract.yaml`.
- Promoted `narrative_source_events` in `config/data_capabilities.yaml` to `gateway_ready` / `unstable`.
- Updated `NarrativeSourceGatewayClient` to issue unified GET requests and preserve Gateway `degraded` status.
- Expanded `run_narrative_source_gateway_probe.py` default source kinds.
- Updated source-quality grouping and dashboard rows for `official_sources`, `open_news_index`, `industry_media`, and the full M20 source-kind set.
- Added candidate inbox and coverage gap report CLIs: `scripts/run_narrative_candidate_inbox.py` and `scripts/run_narrative_source_coverage_gap_report.py`.
- Updated fresh digest to preserve Gateway missing/degraded input diagnostics and prevent non-official/heat-only source kinds from being treated as trusted facts.
- Restored the M20 PM strategy document `docs/product/open-source-first-narrative-data-strategy-2026-06-04.html` into the clean PR branch so `MIK-271` and current brief references resolve.
- Added tests for unified route contract, GET query construction, structured degradation, M20 source-kind coverage, candidate inbox, fresh digest gap diagnostics, and Gateway backlog gap reporting.

## Live Probe

Local Gateway `main` was started at `http://127.0.0.1:8700`. FNI probe completed with 7 source kinds, 0 failed kinds, and 6 rows. `open_news_index` and `social_heat` returned structured Gateway degradations rather than FNI failures.

Generated FNI consumer artifacts from that probe:

- `outputs/fresh_narrative_digest/current/fresh_narrative_digest.json`: degraded, 2 digest items, 5 coverage gaps, 2 degraded inputs.
- `outputs/narrative_candidate_inbox/current/narrative_candidate_inbox.json`: degraded, 2 candidates, 5 coverage gaps.
- `outputs/narrative_source_coverage_gap/current/narrative_source_coverage_gap.json`: degraded, 2 working, 3 missing, 2 degraded, 1 unsupported/Later.
