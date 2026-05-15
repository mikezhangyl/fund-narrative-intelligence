# Reviewed Data Layers Acceptance

## Goal

Require reviewed-mapping enriched acceptance to validate workspace snapshot
`data_layers` for the no-mock-core live path.

## Scope

- Validate the built workspace snapshot includes `workspace-data-layers-v1`.
- Require key live layers such as holdings, valuation snapshots, financial
  metrics, news evidence, and derived signals to be present.
- Require reviewed enriched data layers to contain no mock rows.

## Non-Goals

- No schema changes.
- No provider or report changes.

## Acceptance

- Reviewed enriched acceptance rejects a workspace snapshot with a missing
  financial metrics data layer.
- Live reviewed-mapping enriched acceptance remains green.
