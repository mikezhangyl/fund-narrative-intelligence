# V1 Implementation Spec

This document turns the product thesis into an executable V1 build target. The canonical product thesis remains `fund-narrative-intelligence-system.html`; this file defines the provider strategy, module contracts, scoring rules, reproducibility metadata, degradation behavior, and engineering acceptance criteria.

## V1 Objective

Validate the end-to-end loop:

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

V1 must run without real API credentials by using mock providers. Real providers can be added behind the same interfaces without changing the orchestration flow.

## Data Sources And Provider Strategy

Provider interfaces are part of V1. Real providers are optional in V1, but mock providers are mandatory so the system can run deterministically in local development and tests.

| Data Need | Candidate Real Sources | V1 Provider | Required In V1 | Notes |
| --- | --- | --- | --- | --- |
| Fund holdings | AKShare, Tushare, Eastmoney, Tiantian Fund | `MockFundHoldingProvider` first; real provider adapter later | yes | Must return top holdings with fund-to-stock mapping, weights, as-of date, and source metadata. |
| Stock quotes and liquidity | AKShare, Eastmoney, yfinance | mock first | yes-lite | Used for capital reinforcement and valuation context; V1 can use fixture data. |
| Financials and valuation | Tushare, AKShare, financial reports | mock first | yes-lite | Used for earnings validation and valuation pressure. Missing data must not crash scoring. |
| Announcements | CNINFO, exchange announcements | mock first | yes-lite | Used as evidence events. Real ingestion can be deferred. |
| News and market language | finance news sources, search APIs, crawlers | mock first | yes-lite | Used for narrative momentum and counter evidence. |
| Narrative registry | human-approved local registry | local fixture file | yes | V1 should load a stable registry from local structured data. |
| Signal events and states | derived from evidence/events | local fixture file plus aggregation | yes-lite | V1 needs enough signal state data to score sample funds. |
| LLM calls | OpenAI-compatible provider or local stub | disabled by default; stub allowed | optional | V1 mapping can be fixture/rule based. Any LLM use must be replaceable by deterministic fixtures. |

Current provider implementation:

- `mock`: deterministic local fixtures.
- `real`: compatibility mode that currently records fallback to mock.
- `eastmoney`: no-key Eastmoney/Tiantian Fund holdings adapter for fund holdings only; local fixtures still provide narrative registry, mapping, evidence, and signals.

Provider outputs must include:

- `provider_name`
- `provider_version`
- `source_url` when available
- `as_of_date`
- `retrieved_at`
- `data_quality`
- `confidence_multiplier`

## Degradation Strategy

The pipeline should complete whenever enough data exists to produce a bounded report. Provider failure should reduce confidence and surface data quality, not crash the full run.

| Condition | Behavior | Data Quality | Confidence Impact |
| --- | --- | --- | --- |
| Real provider unavailable | Fall back to configured mock provider if allowed | `mock` | multiply affected confidence by `0.50` |
| Partial provider response | Continue with available fields and mark missing fields | `partial` | multiply by `0.75` |
| Stale data | Continue and expose `as_of_date` in output | `stale` | multiply by `0.60` |
| Required field missing after fallback | Use neutral scoring default for that dimension | `unavailable` | dimension confidence becomes `0` |
| Evidence unavailable | Generate report with explicit evidence gap | `partial` or `unavailable` | lower narrative confidence |

V1 must never silently hide degraded data. JSON outputs and reports should show data quality at the fund, narrative, and evidence level.

## Module Responsibility Matrix

| Module | Input | Output | Calls LLM | Mockable | V1 |
| --- | --- | --- | --- | --- | --- |
| CLI / Main | `fund_code`, provider mode, output directory | run configuration and exit code | no | yes | yes |
| Orchestrator | run configuration | ordered execution result and artifact paths | no | yes | yes |
| Fund Holding Provider | fund code | fund profile and top holdings | no | yes | yes |
| Narrative Registry | registry fixture or store | approved narratives, hierarchy, aliases, version | no | yes | yes |
| Stock Narrative Mapping | holdings, registry, optional evidence | stock-to-narrative mappings with weights and confidence | optional | yes | yes |
| Fund Narrative Aggregation | holdings, stock mappings | primary and secondary narrative exposures | no | yes | yes |
| Evidence Service | provider events, fixtures, source metadata | raw evidence records | optional for extraction | yes | yes-lite |
| Signal Service | evidence records, signal fixtures | signal events and rolling signal states | no | yes | yes-lite |
| Scoring Service | narrative exposures, signal states, data quality | dimension scores, sustainability score, stage, confidence | no | yes | yes |
| Report Writer | fund, holdings, narratives, scores, evidence | Markdown and HTML reports | optional for wording | yes | yes |
| Snapshot Writer | all structured run data | raw JSON and scoring JSON artifacts | no | yes | yes |

## V1 Scoring Rules

Scores use a `0..100` scale. For risk dimensions, higher means more risk. For support dimensions, higher means stronger support.

Required V1 dimensions:

- `earnings_score`: strength of earnings, guidance, orders, margins, and business validation.
- `capital_score`: strength of fund flow, liquidity, ETF/institutional interest, and turnover support.
- `valuation_risk_score`: degree to which valuation looks stretched or fragile.
- `momentum_score`: strength and freshness of market language around the narrative.
- `counter_evidence_risk_score`: intensity of evidence against the narrative.

### Signal To Dimension Mapping

| Dimension | Supporting Signals | Negative / Risk Signals |
| --- | --- | --- |
| `earnings_score` | `revenue_growth_up`, `guidance_raise`, `margin_expansion`, `order_growth` | `demand_slowdown`, `guidance_cut`, `margin_pressure`, `inventory_build` |
| `capital_score` | `institutional_inflow`, `etf_inflow`, `volume_breakout`, `relative_strength_up` | `institutional_outflow`, `etf_outflow`, `liquidity_drop` |
| `valuation_risk_score` | `valuation_extreme`, `multiple_expansion_fast`, `crowded_positioning` | `valuation_reset`, `earnings_catchup` |
| `momentum_score` | `news_frequency_up`, `research_mentions_up`, `management_mentions_up`, `keyword_breakout` | `language_decay`, `coverage_drop` |
| `counter_evidence_risk_score` | `demand_slowdown`, `margin_pressure`, `regulatory_risk`, `order_cancel`, `technology_substitution`, `policy_tightening` | `risk_resolved`, `policy_support` |

### Decay

Every signal event must be decayed before scoring:

```text
decayed_strength = strength * confidence * confidence_multiplier * 0.5 ^ (age_days / half_life_days)
```

If `half_life_days` is missing, V1 defaults to `45`.

### Dimension Score Formula

For support dimensions:

```text
positive_pressure = weighted_average(decayed_strength of supporting signals)
negative_pressure = weighted_average(decayed_strength of negative signals)
score = clamp(round(50 + 50 * positive_pressure - 50 * negative_pressure), 0, 100)
```

For risk dimensions:

```text
risk_pressure = weighted_average(decayed_strength of risk signals)
mitigation_pressure = weighted_average(decayed_strength of mitigating signals)
score = clamp(round(50 + 50 * risk_pressure - 25 * mitigation_pressure), 0, 100)
```

When a dimension has no usable data, V1 returns:

```json
{
  "score": 50,
  "confidence": 0,
  "data_quality": "unavailable"
}
```

### Sustainability Score

```text
sustainability_score =
  0.25 * earnings_score +
  0.20 * capital_score +
  0.20 * momentum_score +
  0.15 * (100 - valuation_risk_score) +
  0.20 * (100 - counter_evidence_risk_score)
```

Narrative confidence should combine mapping confidence, signal confidence, evidence density, freshness, and data quality:

```text
confidence = weighted_average(
  mapping_confidence,
  signal_confidence,
  evidence_density_confidence,
  freshness_confidence,
  data_quality_confidence
)
```

### Score To Stage

V1 stages are heuristic and versioned by `scoring_model_version`.

| Stage | V1 Rule |
| --- | --- |
| `emerging` | `momentum_score >= 60`, `earnings_score < 60`, evidence density low or medium, counter risk `< 60`. |
| `strengthening` | `sustainability_score >= 60`, `momentum_score >= 60`, counter risk `< 60`, valuation risk `< 75`. |
| `expanding` | `sustainability_score >= 70`, earnings and capital both `>= 60`, counter risk `< 60`. |
| `crowded` | valuation risk `>= 75` and capital or momentum `>= 65`, while counter risk `< 65`. |
| `diverging` | support signals remain visible but counter risk `>= 60`, or earnings score `< 50` while capital or momentum `>= 60`. |
| `weakening` | `sustainability_score < 50` and momentum `< 50`, or counter risk `>= 70`. |
| `dead` | `sustainability_score < 35`, momentum `< 35`, and no meaningful positive fresh evidence. |

If multiple rules match, V1 applies this precedence:

`dead -> weakening -> diverging -> crowded -> expanding -> strengthening -> emerging`

## Versioning And Reproducibility

Every raw JSON, scoring JSON, and report must include version metadata.

Required metadata:

- `run_id`
- `fund_code`
- `created_at`
- `as_of_date`
- `provider_set_version`
- `narrative_registry_version`
- `signal_schema_version`
- `scoring_model_version`
- `report_template_version`
- `input_hash`
- `data_snapshot_id`

V1 version defaults:

```json
{
  "provider_set_version": "mock-v1",
  "narrative_registry_version": "registry-v1",
  "signal_schema_version": "signals-v1",
  "scoring_model_version": "scoring-v1",
  "report_template_version": "report-v1"
}
```

Outputs should be reproducible from the raw JSON snapshot plus local registry and signal fixtures with matching versions.

## Deferred But Structured Capabilities

V1 does not implement these capabilities, but it must preserve fields and model boundaries so they can be added later.

| Capability | V1 Does Not Do | Structure To Preserve |
| --- | --- | --- |
| Historical replay | no full replay engine | save raw and scoring snapshots with version metadata and `as_of_date`. |
| Alerting | no notifications or monitors | include nullable `previous_state`, `state_change`, and `state_change_reason`. |
| Workspace UI | no frontend workspace | keep output JSON normalized and workspace-ready. |
| Auto narrative discovery | no automatic registry mutation | include `candidate_narrative` shape and `human_review_status`. |
| Signal governance | no automatic signal promotion | include `signal_schema_version` and allow unknown signals to become candidates. |
| Human review workflow | no review UI | include `human_review_status`, `reviewed_by`, and `reviewed_at` as nullable fields where applicable. |

## Engineering Acceptance Criteria

The first implementation milestone is accepted when this command works without real API credentials:

```bash
python -m src.main --fund-code 000001
```

The CLI should also expose available local fixtures:

```bash
python -m src.main --list-fixtures
```

V1 should support running every local fixture for regression checks:

```bash
python -m src.main --run-all-fixtures
```

V1 should support a live Eastmoney smoke set:

```bash
python -m src.main --run-real-smoke
```

And can explicitly try the Eastmoney holdings adapter:

```bash
python -m src.main --fund-code 161725 --provider-mode eastmoney
```

It must create:

```text
outputs/fund_000001_raw.json
outputs/fund_000001_scoring.json
outputs/fund_000001_report.md
outputs/fund_000001_report.html
```

The generated artifacts must satisfy:

- `raw.json` includes fund profile, holdings, provider metadata, narrative registry version, evidence records, and signal events or states.
- `scoring.json` includes narrative exposures, five dimension scores, sustainability score, lifecycle stage, confidence, data quality, and version metadata.
- `report.md` and `report.html` include fund basics, top holdings, one primary narrative, two to three secondary narratives, evidence summaries, risk evidence, confidence/data-quality notes, and a non-investment-advice disclaimer.
- `report.html` renders semantic HTML sections and tables rather than displaying raw Markdown syntax.
- The command exits non-zero only for invalid user input or unrecoverable local errors.
- Provider unavailability produces degraded output instead of an unhandled exception.
- Missing local mock fixtures and invalid provider payloads produce controlled errors.
- The mock-provider path includes multiple scenario funds so lifecycle stages are not validated only against one happy path.
- The `eastmoney` provider mode can normalize no-key fund holdings while keeping non-holdings intelligence layers local in V1.
- Reports include mapping coverage, mapping method counts, and unmapped holdings when any holdings cannot be mapped.
- Reports include deterministic stage, risk, and confidence interpretation notes without buy/sell/hold recommendations.
- The real-fund smoke set records coverage, primary narrative, stage, unmapped holdings, and pass/fail status.
- The real-fund smoke set writes summary artifacts even when an individual fund fails, marking only that fund as failed and returning a non-zero exit code for the overall smoke command.
- The mock-provider path is deterministic enough for repeatable tests.
