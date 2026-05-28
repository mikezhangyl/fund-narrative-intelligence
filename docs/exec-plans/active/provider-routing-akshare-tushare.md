# Provider Routing For AKShare And Tushare

## Goal

Prepare the provider layer so the project can switch between `AKShare`,
`Tushare`, and existing public-source adapters by configuration instead of
hard-coding one source per data layer.

This slice should build the routing framework first, then connect the highest
value structured providers in later slices.

## Why This Slice Exists

- The current real pipeline mixes `Eastmoney`, `Yahoo`, `CNInfo`, Google News,
  and Sina News directly in orchestration code.
- The next stage needs explicit support for paid `Tushare` access plus open
  `AKShare` coverage.
- Different data layers benefit from different primary sources, so the system
  should support switching, fallback, and later merge behavior.

## Scope

- Define provider-routing configuration per data layer.
- Support `primary` and `fallback` selection without changing artifact
  contracts.
- Keep routing separate for:
  - holdings
  - market quotes
  - valuation snapshots
  - financial metrics
  - announcements
  - news evidence
- Preserve provider provenance fields in generated artifacts:
  - `provider_name`
  - `provider_version`
  - `source_url`
  - `data_quality`
  - `degradation_events`
- Add tests for layer routing and fallback behavior.

## Out Of Scope

- Full `AKShare` integration for every layer
- Full `Tushare` integration for every layer
- Provider merge semantics across multiple successful sources
- Frontend controls for provider selection
- Secret management UI for paid provider credentials

## Proposed Order

1. Add a routing config object and route each layer through it.
2. Keep current default behavior unchanged when no routing config is supplied.
3. Add `Tushare` adapters for the highest-value structured layers first:
   - financial metrics
   - valuation snapshots
4. Add `AKShare` adapters for open-data complement layers:
   - market quotes
   - selected fundamentals where coverage is acceptable
5. Leave merge mode for a later slice after `primary/fallback` is stable.

## Acceptance

- The pipeline can run with no routing config and preserve current behavior.
- A layer can be configured with `primary` plus `fallback` provider names.
- If the primary provider fails, the fallback provider is used and the
  degradation event is recorded.
- Generated artifacts keep the same schema and still disclose provenance.
- Existing single-fund demos and reviewed-mapping acceptance continue to pass.

## Current Status

- Routing is now wired for:
  - holdings
  - market quotes
  - valuation snapshots
  - financial metrics
  - announcements
  - news evidence
- Built-in routed aliases exist for:
  - `tushare` on `financial_metrics`
  - `tushare` on `valuation_snapshots`
  - `akshare` on `market_quotes`
- Default behavior remains unchanged when no routing config is supplied.
- CLI/config entrypoints exist via:
  - `--provider-routing-config`
  - repeatable `--provider-route layer=primary[:fallback]`
- Acceptance commands now include:
  - `python scripts/validate_provider_routing_acceptance.py --output-dir outputs/provider_routing_161725`
  - `python scripts/validate_tushare_primary_acceptance.py --output-dir outputs/tushare_primary_161725`
- The fallback acceptance command now forces `akshare` and `tushare` primaries into an unavailable state during the run so the fallback contract remains deterministic even when `.local.env` or optional provider libraries are present.
- The strict Tushare-primary command reads `TUSHARE_TOKEN` from `.local.env` first and then from the process environment, fails fast when the token is absent, and enforces that valuation and financial routing stay on Tushare even if the selected Tushare provider reports partial row-level degradation.

## Suggested First Targets

- `financial_metrics`:
  `Tushare -> Eastmoney`
- `valuation_snapshots`:
  `Tushare -> Eastmoney`
- `market_quotes`:
  `AKShare -> Eastmoney/Yahoo`

## Non-Goals For The First Chat

- Do not wire every provider at once.
- Do not start with Hong Kong announcements or community-discussion sources.
- Do not refactor unrelated demo rendering or reviewed-mapping logic.
