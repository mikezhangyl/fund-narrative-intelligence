# Reviewed Mapping Valuation Acceptance

## Goal

Include quote-derived valuation snapshots in the strict reviewed-mapping
enriched acceptance path.

## Scope

- Add `--include-valuation-snapshots` to reviewed-mapping acceptance, alongside
  `--include-market-quotes`.
- Require raw/scoring outputs to include `valuation_snapshots`.
- Require the provider foundation, source table, and workspace snapshot to
  preserve a non-mock `Valuation` layer with quote-derived context disclosure.

## Non-Goals

- No fundamental valuation provider.
- No scoring weight changes.
- No frontend implementation.

## Acceptance

- Reviewed-mapping acceptance tests cover valuation snapshots and layer
  provenance.
- Live reviewed-mapping acceptance passes and validates the workspace snapshot.
- Full quality gates pass before merge.
