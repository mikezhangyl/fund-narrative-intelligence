# Workspace Data Layers

## Goal

Add a workspace-snapshot `data_layers` section so future web screens can render
provider payload availability and row counts without re-reading raw/scoring
artifacts.

## Scope

- Add `data_layers` to `workspace-snapshot-v1`.
- Summarize holdings, evidence, signal events, and optional provider payloads.
- Include source layer, provider, data quality, mock flag, source URL, and item
  counts.
- Validate identity and source-layer consistency.

## Non-Goals

- No UI work.
- No duplication of full raw payloads inside the snapshot.
- No scoring changes.

## Acceptance

- Workspace snapshot tests assert mock baseline and optional provider layer
  summaries.
- Workspace validation rejects malformed `data_layers`.
- V1 acceptance and reviewed-mapping enriched acceptance stay green.
