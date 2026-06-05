# Implementation Notes

## Summary

FNI now consumes Gateway narrative source events through the unified provider-neutral route:

`GET /api/v1/market-data/narrative/source-events`

The FNI client no longer defaults to per-source POST routes for source-event probing. It supports the M20 source kinds `official_filings`, `official_disclosures`, `official_sources`, `news_context`, `open_news_index`, `industry_media`, and `social_heat`.

## Key Changes

- Added unified Gateway endpoint to `config/market_data_gateway_contract.yaml`.
- Promoted `narrative_source_events` in `config/data_capabilities.yaml` to `gateway_ready` / `unstable`.
- Updated `NarrativeSourceGatewayClient` to issue unified GET requests and preserve Gateway `degraded` status.
- Expanded `run_narrative_source_gateway_probe.py` default source kinds.
- Updated source-quality grouping for `official_sources`, `open_news_index`, and `industry_media`.
- Added tests for unified route contract, GET query construction, structured degradation, and M20 source-kind coverage.

## Live Probe

Local Gateway `main` was started at `http://127.0.0.1:8700`. FNI probe completed with 7 source kinds, 0 failed kinds, and 6 rows. `open_news_index` and `social_heat` returned structured Gateway degradations rather than FNI failures.
