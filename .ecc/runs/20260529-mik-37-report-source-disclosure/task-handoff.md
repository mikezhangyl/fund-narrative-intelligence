# Task Handoff

## Goal

Expose narrative and market-data source diagnostics in report JSON and Chinese HTML for the three fund narrative reports.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

Added shared report source disclosure helpers, top-level `market_data_source` payloads, aggregate market-data source propagation through comparison and matrix reports, and Chinese HTML rows for source status, fallback source, and warning summaries.

## Commands Run

See `verification.md`.

## Test Results

Targeted red/green tests, report test suite, service acceptance, ruff, compileall, and diff check passed.

## Known Risks And Assumptions

Market data source is inferred from report input rows plus provider degradation/failure events. Future provider classes can enrich it by exposing `provider_name`, `data_fetch_mode`, and `degradation_events`.

## Suggested Quality Checks

When adding new formal reports, add `narrative_source`/`market_data_source` JSON and Chinese HTML disclosure tests before implementation.
