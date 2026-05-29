# Live Validation Dashboard Taxonomy - 2026-05-29

Linear issues: `MIK-62`, `MIK-54`, `MIK-93`, `MIK-88`

## Purpose

Round 2 live validation must separate deterministic local checks from live gateway/provider checks.
Missing local configuration is not a failing test;
it is an explicit operational state.

The dashboard script is:

```bash
uv run python scripts/run_live_validation_dashboard.py
```

It writes JSON and Chinese HTML under `outputs/live_validation_dashboard/` by
default.

## Configuration

- `MARKET_DATA_GATEWAY_URL`: local stock-data-gateway HTTP boundary.
- `NARRATIVE_SERVICE_URL`: local Narrative Service HTTP boundary.
- `--timeout-seconds`: bounded request timeout for every live probe.

FNI must call only configured local gateway or Narrative Service HTTP boundaries.
It must not directly call Tushare, AkShare, EastMoney, news websites, browser
automation, proxy, CAPTCHA, or anti-detect infrastructure from this dashboard.

## Round 4 Credential-Safe Status Taxonomy

Round 4 upgrades the dashboard taxonomy so it can act as a live provider
credential smoke surface without leaking secrets or collapsing partial provider
failures into an all-or-nothing result.

- `configured`: required local boundary configuration exists; no secret value is
  returned.
- `not_configured`: required URL is absent. Alias: `missing_config`.
- `reachable`: configured boundary responded, but no business contract was
  evaluated.
- `provider_permission_required`: provider or gateway route requires permission,
  credential, quota, or authorization.
- `request_timeout`: bounded request timed out without failing the whole smoke
  run.
- `upstream_degraded`: configured boundary returned degraded payload, warnings,
  or upstream instability.
- `schema_mismatch`: configured boundary responded with an unexpected or empty
  contract shape.
- `contract_failed`: configured boundary failed the expected HTTP or JSON
  contract.
- `success`: configured probe returned usable payload data.

Each row includes `id`, `owner_service`, `endpoint`,
`required_credential_hint`, `status`, `latency_ms`, `warnings`,
`failure_reason`, and `next_action`. Environment variable names such as
`MARKET_DATA_GATEWAY_URL`, `NARRATIVE_SERVICE_URL`, or provider credential hints
may appear, but secret values must not appear in JSON, HTML, logs, or comments.

Partial failures are expected operational states. A timeout, permission block,
or upstream degraded provider row should produce a bounded row-level diagnostic
and next action, not abort the whole dashboard.

## Round 2 Compatibility Notes

- `passed`: configured probe returned usable payload data.
- `degraded`: configured probe returned data with warnings or degraded status.
- `blocked`: configured endpoint rejected the request, usually auth, rate limit,
  or request semantics.
- `not_configured`: required URL is absent. Alias: `missing_config`.
- `product_gap`: service is reachable, but the requested business data is empty
  or missing.
- `system_failure`: runtime, timeout, network, or server failure prevented
  validation.

## Probe Groups

- `gateway_health`: checks whether the gateway boundary is configured.
- `fund_holdings`: checks gateway-backed fund holdings.
- `daily_bars`: checks gateway-backed daily bars.
- `sector_flow_structure_news`: checks representative gateway sector, flow,
  structure, and news routes.
- `narrative_service`: checks Narrative Service health and ops summary.
- `review_workspace`: checks review queue availability for workspace use.
- `deterministic_local`: checks repo-local contracts that do not require live
  provider configuration.

## Output Contract

Dashboard JSON uses `live-validation-dashboard-v1` and includes:

- `taxonomy`
- `inputs`
- `rows`
- `summary`

Each row includes:

- `id`
- `group`
- `capability`
- `owner_service`
- `mode`
- `status`
- `status_label_zh`
- `source`
- `endpoint`
- `required_credential_hint`
- `latency_ms`
- `row_count`
- `warnings`
- `failure_reason`
- `next_action`
- `message`

## Acceptance Notes

`not_configured` rows are acceptable in deterministic local mode. A live gateway
run becomes more informative when `MARKET_DATA_GATEWAY_URL` is set, but missing
gateway configuration must not block local CI or deterministic release checks.
