# Live Validation Dashboard Taxonomy - 2026-05-29

Linear issues: `MIK-62`, `MIK-54`

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

## Status Taxonomy

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

- `group`
- `capability`
- `mode`
- `status`
- `status_label_zh`
- `source`
- `endpoint`
- `latency_ms`
- `row_count`
- `warnings`
- `message`

## Acceptance Notes

`not_configured` rows are acceptable in deterministic local mode. A live gateway
run becomes more informative when `MARKET_DATA_GATEWAY_URL` is set, but missing
gateway configuration must not block local CI or deterministic release checks.
