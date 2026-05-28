# Market Data Gateway Boundary

This document records the FNI market-data ownership boundary for Linear
`MIK-45`.

## Decision

External market-data source expansion is owned by the local
`stock-data-gateway` project. FNI consumes provider-neutral gateway contracts,
records capability status, and renders source/degradation diagnostics in
reports and probes.

FNI may keep direct external providers only as narrow compatibility shims,
deterministic test fixtures, or temporary fallback adapters while gateway
routes are being accepted. New source breakthroughs should be requested through
gateway change-request documents under:

`/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/`

## Dataset Ownership

FNI records dataset status in `config/data_capabilities.yaml`:

- `available`: can run today through a report/probe path.
- `unstable`: reachable but not reliable enough to claim stable production use.
- `missing`: not currently collectable.
- `planned`: intentionally future work.
- `disabled`: implemented path exists but should not be used.

FNI records gateway posture with:

- `gateway_ready`: FNI has a gateway consumption path.
- `gateway_owned`: the gateway must own acquisition/cache behavior before FNI
  treats the dataset as a capability.
- `gateway_planned`: the dataset should move behind the gateway but is not yet
  available there.
- `direct_only`: legacy or local-only path; new external data work should not
  use this without an explicit exception.

`config/market_data_gateway_contract.yaml` remains the consumer contract for
gateway routes. Every available non-planned gateway contract dataset should be
represented in `config/data_capabilities.yaml`.

## Source And Degradation Disclosure

Reports and probes must expose enough diagnostics to distinguish:

- gateway-backed data;
- local fallback/test fixtures;
- direct compatibility adapters;
- degraded gateway responses;
- missing or unstable datasets.

JSON output should keep machine-readable fields such as `data_fetch_mode`,
`narrative_source`, `degradation_events`, `failures`, or capability-specific
source summaries. Reader-facing HTML should show the same risk in plain
Chinese when the report is formal reader-facing output.

## Change Request Rule

When FNI needs a new external market-data source, the default path is:

1. Update the FNI consumer need in `config/data_capabilities.yaml` or the
   relevant product plan.
2. Write a gateway change request in the gateway project's product docs.
3. Wait for the gateway route to expose a normalized or documented
   compatibility surface.
4. Add FNI probes/reports against the gateway API.
5. Mark the dataset `available` or `unstable` based on smoke and report output.

FNI should not add direct Tushare, AkShare, EastMoney, or news-site integrations
for new source expansion unless the change is explicitly scoped as a temporary
compatibility shim.

## Can-Do Versus Stable

`Can-Do` means the route/report can demonstrate the intended capability with
bounded diagnostics. It does not mean production reliability.

`stable` requires repeated live checks, acceptable failure behavior, and enough
cache/gateway operational evidence to trust the path for repeated report use.
