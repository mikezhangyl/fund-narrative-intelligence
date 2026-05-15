# Reviewed Optional Data Layers

## Goal

Make reviewed-mapping enriched acceptance require all optional provider payloads
that the run intentionally enables and reports.

## Scope

- Require workspace `data_layers` for `announcements`.
- Require workspace `data_layers` for `announcement_evidence`.
- Require workspace `data_layers` for `market_quotes`.
- Preserve existing requirements for holdings, valuation snapshots, financial
  metrics, news evidence, and derived signal events.

## Non-Goals

- No new provider implementation.
- No frontend UI.
- No report rendering changes.

## Acceptance

- Tests fail first when optional announcement/market quote layers are omitted.
- Reviewed-mapping enriched acceptance rejects missing optional provider
  `data_layers`.
- Standard quality gates pass, then the slice is merged and pushed.
