# Gateway Narrative Source Change Request Protocol - 2026-05-29

Linear issue: `MIK-67`

## Decision

New narrative source capabilities should be requested from `stock-data-gateway`
before FNI adds direct external provider access.

FNI's default source expansion rule is `gateway_change_request_first`.

## Required Change Request Fields

Every new narrative source request should include:

- dataset
- provider preference
- endpoint semantics
- fallback behavior
- validation matrix
- sample consumer request
- freshness expectation
- degradation behavior
- permission or credential expectation
- source event fields produced for FNI

## Template

```markdown
# FNI Narrative Source Capability Request - <date>

## Dataset

<dataset name and product use>

## Provider Preference

1. gateway-normalized provider
2. provider-specific upstream fallback, if already gateway-owned
3. local fixture only for deterministic tests

## Endpoint Semantics

- route
- method
- query/body fields
- normalized response fields
- pagination or time-window behavior

## Fallback Behavior

- missing config
- upstream timeout
- empty business data
- provider permission denied

## Validation Matrix

| Scenario | Expected Status | Required Fields |
| --- | --- | --- |
| configured with rows | passed | source event rows |
| configured but empty | product_gap | empty rows with metadata |
| timeout/degraded upstream | degraded | warnings |
| missing credential | blocked | credential warning |

## Sample Consumer Request

```bash
curl "$MARKET_DATA_GATEWAY_URL/api/v1/market-data/news/briefs?limit=5"
```
```

## FNI Responsibilities

- Keep deterministic fixtures for tests.
- Consume accepted gateway routes through HTTP contracts.
- Update `config/data_capabilities.yaml` when gateway acceptance state changes.
- Convert gateway rows into `source-event-schema-v1` records before candidate
  narrative intake.

## Non-Goals

- Do not implement gateway endpoints inside FNI.
- Do not add direct Tushare, AkShare, EastMoney, or news-site integrations in
  FNI for new source expansion.
- Do not add browser automation, proxy, CAPTCHA, or anti-detect infrastructure.
