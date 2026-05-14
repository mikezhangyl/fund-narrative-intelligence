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

V1 also emits a run-level `provider_foundation` object in raw and scoring JSON. It separates provenance for these layers:

- `holdings`
- `narrative_registry`
- `stock_mappings`
- `evidence`
- `signals`

`provider_foundation.effective_data_quality` is the quality used for scoring confidence and user-facing reports. For example, an Eastmoney holdings run with mock registry, mapping, evidence, and signals is `partial`, not `fresh`.

Current provider-layer interfaces:

| Interface | V1 Mock Implementation | Current Behavior |
| --- | --- | --- |
| `NarrativeRegistryProvider` | `MockNarrativeRegistryProvider` | loads `narrative_registry.json`. |
| `StockNarrativeMappingProvider` | `MockStockNarrativeMappingProvider` | loads `stock_narrative_mappings.json`. |
| `EvidenceProvider` | `MockEvidenceProvider` | loads `evidence.json`. |
| `SignalEventProvider` | `MockSignalEventProvider` | loads `signal_events.json`. |
| `MarketDataProvider` | `MockMarketDataProvider` | returns an explicit empty mock quote payload. |
| `ValuationProvider` | `MockValuationProvider` | returns an explicit empty mock valuation payload. |
| `AnnouncementProvider` | `MockAnnouncementProvider` | returns an explicit empty mock announcement payload. |
| `NewsEvidenceProvider` | `MockNewsEvidenceProvider` | returns an explicit empty mock news evidence payload. |

The empty mock providers are deliberate placeholders. They preserve V1 contracts without pretending that real quote, valuation, announcement, or news ingestion exists.

Optional real-provider adapter foundation:

- `CNInfoAnnouncementProvider` targets CNINFO announcement search and normalizes announcement metadata into the V1 announcement-provider contract.
- It is not called by the default report pipeline yet.
- It must use an injectable fetcher in tests.
- It should infer the CNINFO market column from stock-code prefixes and reject invalid stock codes without calling the external provider.
- Provider failures must return an `unavailable` payload and record `provider_unavailable` rather than crash orchestration.

Optional announcement-to-evidence conversion:

- `convert_announcements_to_evidence` turns announcement metadata into V1 evidence records.
- It maps each announcement stock code through existing stock-to-narrative mappings and emits one evidence record per mapped narrative.
- It uses conservative deterministic title/category keyword rules for `earnings`, `orders`, `capital_flow`, `risk`, `financial_report`, `governance`, and generic `announcement` evidence types.
- Evidence confidence is `classification_base_confidence * mapping_confidence * data_quality_confidence`.
- The converter must not download or parse PDFs in V1. Generated summaries must state that only announcement metadata was classified.
- Unmapped or malformed announcements must be tracked and skipped without crashing the caller.

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

Reports must include a visible `Data Source Notice` whenever `provider_foundation.disclosure_required` is true. This includes pure mock runs, fallback-to-mock runs, and mixed runs where only some layers are real. The notice must state which layers are mock-backed and list degradation events such as `provider_fallback`.

## Stock Narrative Mapping Transparency

V1 must not treat stock-to-narrative mapping as an opaque assertion. Every selected mapping should produce a structured `mapping_rationales` row in raw JSON, scoring JSON, Markdown reports, and HTML reports.

Required `mapping_rationales` fields:

- `stock_code`
- `stock_name`
- `industry`
- `narrative_id`
- `narrative_name`
- `method`
- `confidence`
- `mapping_weight`
- `matched_terms`
- `needs_review`
- `precision_flag`
- `reason`

For explicit fixture mappings, `reason` should state that the mapping came from the stock-narrative mapping fixture. For `registry_term_rule` fallback mappings, `matched_terms` should list the registry aliases or related terms that matched the holding's stock code, stock name, or industry. If a fallback match maps one stock to multiple narratives, the rationale must preserve `needs_review` and `precision_flag` so users can see that the mapping is lower-confidence.

V1 precision tiers:

| Condition | Confidence | Precision Flag | Review Action |
| --- | ---: | --- | --- |
| Explicit fixture mapping | mapping fixture value | none | none |
| Single fallback with stock-name, stock-code, product, or mixed terms | `0.52` | none | none |
| Single fallback supported only by holding industry terms | `0.48` | `broad_industry_fallback` | `curation_review` |
| Fallback maps one holding to multiple narratives | `0.42` | `multi_match_fallback` | `manual_review` |

If multiple precision concerns apply, `multi_match_fallback` takes precedence because a multi-narrative assignment is a stronger review signal than a single broad industry-only match.

V1 can also use explicit `mapping_exclusions` for known-bad fallback candidates. Exclusions apply to fallback candidates only, not curated fixture mappings. Excluded candidates must not enter narrative aggregation or scoring. Raw JSON, scoring JSON, reports, and real-smoke summaries should include `excluded_mapping_candidates` with stock, candidate narrative, matched terms, reason, and `recommended_action`.

V1 preserves review-only `candidate_narratives` in the registry. Candidate narratives can be linked to exclusions through `related_exclusion_ids` and `triggering_stock_codes`; in-scope candidates should be emitted in raw/scoring JSON and reports, but they must not enter active stock mapping, aggregation, scoring, or lifecycle-stage output until human review promotes them into `narratives`.

Future approval should happen in a web UI. V1 does not implement the UI, but all candidate/exclusion objects should be shaped for future rendering and action: stable IDs, review status, rationale, source, related stocks, related exclusions, nullable reviewer fields, and timestamps must be preserved in structured output instead of only report prose.

Candidate narrative review actions are explicit state transitions:

| Action | Candidate Status | Active Registry Change | Required Fields |
| --- | --- | --- | --- |
| `approve` | `promoted` / `approved` | append one active narrative from supplied promotion metadata | `action_id`, `candidate_narrative_id`, `reviewed_by`, `reviewed_at`, `review_note`, `promotion.narrative_id`, `promotion.parent_id`, `promotion.level`, `promotion.aliases`, `promotion.related_terms` |
| `reject` | `rejected` / `rejected` | none | `action_id`, `candidate_narrative_id`, `reviewed_by`, `reviewed_at`, `review_note` |
| `defer` | `deferred` / `deferred` | none | `action_id`, `candidate_narrative_id`, `reviewed_by`, `reviewed_at`, `review_note` |

The review action function must be immutable: it returns a new registry payload and does not mutate the input registry. V1 report generation must not call this function automatically.

V1 should emit a `candidate_review_queue` object whenever in-scope candidate narratives are present:

```json
{
  "version": "candidate-review-queue-v1",
  "summary": {
    "total_count": 1,
    "pending_count": 1,
    "action_required": true
  },
  "items": [
    {
      "review_item_id": "RQ_C_EXAMPLE",
      "item_type": "candidate_narrative",
      "candidate_narrative_id": "C_EXAMPLE",
      "available_actions": ["approve", "reject", "defer"],
      "default_action": "defer",
      "requires_promotion_metadata": true,
      "related_exclusions": [],
      "promotion_action_template": {}
    }
  ]
}
```

This queue is read-ready for a future web workspace. It should not persist review actions or mutate the registry by itself.

The pipeline should also write a dedicated review queue artifact:

```text
outputs/fund_<fund_code>_review_queue.json
```

This artifact should include `metadata`, `fund`, `provider_foundation`, `candidate_review_queue`, `candidate_narratives`, and `excluded_mapping_candidates`.

V1 should also expose a safe local preview wrapper for future web review-action
submissions:

```bash
python -m src.main --preview-review-action path/to/action.json
```

The wrapper reads a review action JSON payload, applies it to a copy of the
registry, and writes a `candidate_review_action_<action_id>_preview.json`
artifact. The preview includes the submitted action, summary fields,
`source_registry_mutated`, `source_registry_written`,
`requires_explicit_persistence_step`, `registry_delta`, and `result_registry`.
`registry_delta` should list active narrative IDs added, active narrative count
change, and before/after candidate review state so future web screens can render
the effect without diffing the full registry. It must not write back to
`data/fixtures/narrative_registry.json` unless a separate future persistence
workflow is explicitly added and approved. If an explicit `--review-action-output`
path is provided, it must remain inside `--output-dir` and must not overwrite the
registry or action input files.

## Module Responsibility Matrix

| Module | Input | Output | Calls LLM | Mockable | V1 |
| --- | --- | --- | --- | --- | --- |
| CLI / Main | `fund_code`, provider mode, output directory | run configuration and exit code | no | yes | yes |
| Orchestrator | run configuration | ordered execution result and artifact paths | no | yes | yes |
| Fund Holding Provider | fund code | fund profile and top holdings | no | yes | yes |
| Narrative Registry | registry fixture or store | approved narratives, hierarchy, aliases, version | no | yes | yes |
| Stock Narrative Mapping | holdings, registry, optional evidence | stock-to-narrative mappings, mapping rationales, weights, confidence, and review flags | optional | yes | yes |
| Fund Narrative Aggregation | holdings, stock mappings | primary and secondary narrative exposures | no | yes | yes |
| Evidence Service | provider events, fixtures, source metadata, optional announcement metadata | raw evidence records | optional for extraction | yes | yes-lite |
| Signal Service | evidence records, signal fixtures | signal events and rolling signal states | no | yes | yes-lite |
| Scoring Service | narrative exposures, signal states, data quality | dimension scores, sustainability score, stage, confidence | no | yes | yes |
| Report Writer | fund, holdings, narratives, scores, evidence | Markdown and HTML reports | optional for wording | yes | yes |
| Snapshot Writer | all structured run data | raw JSON and scoring JSON artifacts | no | yes | yes |
| Candidate Review Workflow | candidate review action, registry payload | preview artifact or immutable result registry | no | yes | yes |

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
| `strengthening` | `sustainability_score >= 60`, `momentum_score >= 60`, counter risk `< 60`, valuation risk `< 75`; or `sustainability_score >= 55`, earnings `>= 65`, momentum `>= 60`, counter risk `< 60`, valuation risk `< 75`. |
| `expanding` | `sustainability_score >= 70`, earnings and capital both `>= 60`, counter risk `< 60`. |
| `crowded` | valuation risk `>= 75` and capital or momentum `>= 65`, while counter risk `< 65`. |
| `diverging` | support signals remain visible but counter risk `>= 60`, or earnings score `< 50` while capital or momentum `>= 60`. |
| `weakening` | `sustainability_score < 50` and momentum `< 50`, counter risk `>= 70`, `sustainability_score < 50` with counter risk `>= 60`, or `sustainability_score < 45` with earnings `< 45`. |
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
| Workspace UI | no frontend workspace | keep output JSON normalized and workspace-ready for future web review/approval screens. |
| Auto narrative discovery | no automatic registry mutation | include `candidate_narratives` with `human_review_status`, `related_exclusion_ids`, and `triggering_stock_codes`. |
| Signal governance | no automatic signal promotion | include `signal_schema_version` and allow unknown signals to become candidates. |
| Human review workflow | no review UI yet; future review happens on the web | include stable IDs, `human_review_status`, rationale, related object links, `reviewed_by`, and `reviewed_at` as nullable fields where applicable. |

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

V1 should support provider diagnostics without writing report artifacts:

```bash
python -m src.main --fund-code 000001 --provider-diagnostics
```

V1 can optionally include CNINFO announcement metadata as evidence:

```bash
python -m src.main --fund-code 000001 --include-cninfo-announcements --announcement-start-date 2026-05-01
```

This option is off by default. When enabled, raw/scoring JSON must include `announcements` and `announcement_evidence`, provider foundation must include an `announcements` layer, and reports must disclose that announcement evidence is metadata-only.

V1 should also support a live announcement-evidence smoke command:

```bash
python -m src.main --run-announcement-smoke
```

The smoke command should validate an A-share fund example with Eastmoney holdings plus CNINFO announcement metadata. It must fail if CNINFO returns no announcements, if announcement metadata is not converted into evidence, if the provider foundation lacks a non-mock `Announcements` layer, or if the report data lacks a visible mixed/mock data-source notice.

V1 should support previewing a future web candidate-review action without
requiring a fund code:

```bash
python -m src.main --preview-review-action path/to/action.json
```

The preview command must write a preview artifact only. It must not mutate the
source registry fixture, must reject output paths that overwrite source inputs or
escape `--output-dir`, and must not silently promote a candidate during normal
report generation.

And can explicitly try the Eastmoney holdings adapter:

```bash
python -m src.main --fund-code 161725 --provider-mode eastmoney
```

It must create:

```text
outputs/fund_000001_raw.json
outputs/fund_000001_scoring.json
outputs/fund_000001_review_queue.json
outputs/fund_000001_report.md
outputs/fund_000001_report.html
```

The generated artifacts must satisfy:

- `raw.json` includes fund profile, holdings, provider metadata, narrative registry version, evidence records, and signal events or states.
- `scoring.json` includes narrative exposures, five dimension scores, sustainability score, lifecycle stage, confidence, data quality, and version metadata.
- `review_queue.json` includes the workspace-ready candidate review queue and the candidate/exclusion context needed to render it.
- `report.md` and `report.html` include fund basics, top holdings, one primary narrative, two to three secondary narratives, evidence summaries, risk evidence, confidence/data-quality notes, and a non-investment-advice disclaimer.
- `report.html` renders semantic HTML sections and tables rather than displaying raw Markdown syntax.
- The command exits non-zero only for invalid user input or unrecoverable local errors.
- Provider unavailability produces degraded output instead of an unhandled exception.
- Missing local mock fixtures and invalid provider payloads produce controlled errors.
- The mock-provider path includes multiple scenario funds so lifecycle stages are not validated only against one happy path.
- The `eastmoney` provider mode can normalize no-key fund holdings while keeping non-holdings intelligence layers local in V1.
- Reports include mapping coverage, mapping method counts, and unmapped holdings when any holdings cannot be mapped.
- Multi-match fallback mappings must be retained but lowered in confidence, marked `needs_review`, and emitted as `mapping_precision_flags`.
- Reports include deterministic stage, risk, and confidence interpretation notes without buy/sell/hold recommendations.
- The real-fund smoke set records coverage, primary narrative, stage, concrete unmapped holding details, and pass/fail status.
- The real-fund smoke set records multi-mapped holdings so high coverage does not hide possible registry precision risks.
- The real-fund smoke set records mapping precision flags so broad-industry and multi-match curation work is visible in the summary JSON and Markdown.
- The real-fund smoke CLI output prints per-fund precision flag, excluded candidate, candidate narrative, and review queue counts so terminal logs do not hide mapping precision or taxonomy review work behind coverage numbers.
- The real-fund smoke set writes summary artifacts even when an individual fund fails, marking only that fund as failed and returning a non-zero exit code for the overall smoke command.
- The announcement-evidence smoke set writes summary artifacts and returns non-zero when CNINFO metadata, evidence conversion, announcement provider disclosure, or mock/mixed data-source notice checks fail.
- The mock-provider path is deterministic enough for repeatable tests.
