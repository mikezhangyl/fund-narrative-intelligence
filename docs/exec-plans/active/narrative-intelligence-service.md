# Narrative Intelligence Service

## Goal

Turn the current static `narrative_registry + stock_mappings + evidence + signals`
stack into a separate narrative intelligence service that can:

- refresh candidate narratives from real-source evidence,
- refresh stock-to-narrative mappings with explicit confidence and provenance,
- synthesize provider-derived evidence and signals into narrative-level state,
- preserve human review as the write gate for durable registry and mapping stores.

## Why Now

The A-share core data path is now largely real for:

- holdings,
- market quotes,
- valuation snapshots,
- financial metrics.

Report quality is now bottlenecked by static or partially reviewed intelligence
layers:

- `narrative_registry`
- `stock_mappings`
- `evidence`
- `signals`

## Non-Goals

- Replace structured source fetching with LLM guessing.
- Build a general multi-agent framework across the whole product.
- Remove human review for registry or mapping promotion.
- Add real-time intraday infrastructure in the first service slice.

## Service Boundary

The narrative intelligence service should own five responsibilities:

1. `registry`
   - active narratives
   - candidate narratives
   - aliases
   - related terms
   - taxonomy metadata

2. `mapping`
   - stock -> narrative mappings
   - mapping confidence
   - mapping rationale
   - exclusion rules

3. `evidence`
   - normalized narrative evidence rows from announcements, news, and later
     additional sources

4. `signals`
   - narrative signal events derived from evidence, quotes, valuation, and
     financial metrics

5. `review`
   - candidate queue
   - promotion preview
   - persistence into reviewed stores

The fund report pipeline should consume this service as a bounded dependency
instead of stitching together fixture-backed pieces itself.

## Target Runtime Shape

### Deterministic Outer Pipeline

Keep the top-level report pipeline deterministic:

`fund holdings -> numeric providers -> narrative intelligence service -> scoring -> report`

### Agentized Inner Intelligence Layer

Use agent-style logic only inside the narrative service, where semantics matter.

Planned internal roles:

1. `source-scout`
   - gathers structured source candidates already fetched by providers
   - does not decide narratives

2. `narrative-curator`
   - proposes candidate narratives
   - proposes aliases and related terms
   - never writes directly to reviewed stores

3. `mapping-analyst`
   - proposes stock -> narrative mappings
   - explains rationale and uncertainty

4. `evidence-synthesizer`
   - clusters multi-source items into narrative evidence
   - marks corroborated / conflicting / low-confidence states

5. `signal-judge`
   - converts evidence + numeric context into signal events
   - remains contract-bound and deterministic at output

6. `review-packager`
   - produces candidate review queue and promotion payloads for human approval

These roles can start as plain Python modules with LLM-ready boundaries. They do
not need to become a distributed agent platform in phase one.

## Data Contracts

### Inputs

- reviewed registry store
- reviewed mapping store
- holdings payload
- announcements payload
- news evidence payload
- market quotes payload
- valuation snapshots payload
- financial metrics payload

### Outputs

- `registry_snapshot`
- `mapping_snapshot`
- `narrative_evidence`
- `signal_events`
- `candidate_narratives`
- `candidate_review_queue`
- `diagnostics`

## Storage Model

Use three storage tiers:

1. `reviewed durable store`
   - existing reviewed registry and reviewed mapping JSON stores
   - human-approved only

2. `derived working snapshot`
   - per-run or per-refresh generated intelligence snapshot
   - may contain low-confidence and conflicting items

3. `review artifacts`
   - candidate queues
   - preview payloads
   - promotion/persistence results

The service should never silently overwrite the durable reviewed store from
agent output.

## Confidence And Uncertainty Policy

Prefer these states over mock fallback:

- `fresh`
- `partial`
- `conflicting`
- `low-confidence`
- `unavailable`

Mock remains last-resort only for deterministic demo or explicit fallback.

## First Implementation Slice

Phase 1 should not try to solve automatic narrative discovery end to end.

Build this first:

1. Add a `NarrativeIntelligenceService` orchestration module.
2. Move current registry/mapping/evidence/signal assembly behind that service.
3. Add a `diagnostics` payload for:
   - unmapped holdings
   - low-confidence mappings
   - missing evidence by narrative
   - conflicting evidence by narrative
4. Keep reviewed stores as the only durable truth.
5. Keep candidate promotion human-gated.

This phase produces a real service boundary without yet depending on LLMs.

## Second Implementation Slice

1. Add `provider-derived` narrative evidence aggregation across:
   - announcements
   - news
   - later research/IR pages
2. Add candidate narrative generation from repeated unmapped holdings and
   repeated source terms.
3. Emit service-level `candidate_narratives` independent of static fixture-only
   candidate definitions.

## Third Implementation Slice

1. Introduce bounded LLM use only in:
   - candidate narrative naming,
   - alias/related-term expansion,
   - evidence clustering,
   - conflict detection,
   - mapping rationale generation.
2. Require explicit source citations and structured output schemas.
3. Never allow the model to fabricate numeric fields or provenance URLs.

## Acceptance Direction

The first acceptance check for this service should prove:

- report generation no longer depends on stitching fixture-backed narrative
  layers directly inside `orchestrator.py`,
- unmapped holdings and low-confidence mappings are exposed through service
  diagnostics,
- candidate review queue still validates and persists through the reviewed-store
  workflow.

## Narrative V1 Execution Knives

Use this as the implementation order for the current narrative V1 lane.

1. `service-boundary`
   - add `NarrativeIntelligenceService`
   - move registry/mapping/evidence/signal assembly behind the service
   - expose service diagnostics
   - status: implemented on 2026-05-15

2. `source-scout`
   - normalize announcements, evidence, quotes, valuation, and financial rows into
     `source_items`
   - emit source-item stats for downstream generation and review
   - status: implemented on 2026-05-15

3. `deterministic-candidate-seeds`
   - derive candidate seeds from unmapped or low-confidence holdings plus repeated
     source terms
   - preserve supporting item ids and trigger stock codes
   - status: implemented on 2026-05-15

4. `narrative-curator`
   - add bounded candidate-curation interfaces
   - default to deterministic output, optionally use OpenAI structured output when
     `OPENAI_API_KEY` is available or explicitly requested
   - status: implemented on 2026-05-15

5. `mapping-analyst`
   - emit review-only candidate mapping proposals from generated candidates
   - include rationale, confidence, and supporting source item ids
   - status: implemented on 2026-05-15

6. `evidence-synthesizer`
   - aggregate active narrative evidence into corroborated / conflicting /
     limited / missing summaries
   - status: implemented on 2026-05-15

7. `review-packager`
   - merge generated candidates into the existing candidate review queue without
     bypassing human-gated promotion
   - status: implemented on 2026-05-15

8. `acceptance`
   - add a dedicated narrative-intelligence validation script and regression
     coverage for generated-candidate runs
   - status: implemented on 2026-05-15

## Narrative Service V2 Redesign

### Why V1 Is Still Unstable

The current V1 lane is structurally useful but semantically unstable for
China-focused fund analysis.

Observed failure modes:

1. active narratives still come from an English-first fixture/reviewed registry
2. runtime mapping still leans on `registry_term_rule` and
   `broad_industry_fallback`
3. candidate generation can see partial evidence, but it does not control the
   active taxonomy
4. company events, quote snapshots, and market narratives are not separated as
   different object types
5. source normalization still carries mixed-language provider residue

Consequence:

The service can produce artifacts and diagnostics, but it cannot yet claim that
the narrative layer itself is a stable Chinese-first intelligence system.

### V2 Goal

Turn the service into a Chinese-first narrative system where:

- the canonical narrative language is Chinese
- company facts are not mistaken for narratives
- stock-to-narrative mapping reflects business-chain exposure instead of broad
  term collision
- LLM use is bounded to Chinese semantic abstraction and explanation
- reviewed stores remain the only durable truth

### Design Principles

1. Chinese is the canonical language
   - every approved narrative must have one Chinese canonical name
   - reports default to Chinese display
   - English terms are aliases only

2. Narrative is a theme, not a company
   - company names, brands, provinces, and one-stock events cannot be promoted
     as narratives by default

3. Registry stability beats generation frequency
   - the registry is a slow-changing layer
   - weekly refresh proposes changes; it does not directly rewrite taxonomy

4. Evidence first, LLM second
   - providers collect facts
   - deterministic logic shapes evidence objects
   - LLM abstracts only after the fact layer is stable

5. Human review remains the write gate
   - no automatic promotion into reviewed registry or reviewed mappings

### Canonical Data Model

V2 should stop treating one `narrative` object as the only semantic layer.

Use four object classes:

1. `company_fact`
   - one company, one event or one metric fact
   - examples:
     - `舍得酒业一季报利润同比下滑`
     - `迎驾贡酒当日价格大幅回撤`

2. `company_exposure_tag`
   - relatively stable company business labels
   - examples:
     - `高速光模块`
     - `白酒`
     - `海缆`
     - `算力服务器代工`

3. `sector_theme_signal`
   - recurring cross-company signals inferred from facts
   - examples:
     - `白酒需求分化`
     - `光模块景气持续`
     - `海缆资本开支回暖`

4. `narrative`
   - the reviewed, reportable market theme used for fund-level aggregation
   - examples:
     - `AI光互联基础设施`
     - `高端白酒消费分化`
     - `通信与电力基础设施`

Only the fourth object becomes the durable narrative registry surface. The
first three exist to prevent the service from collapsing too early into a
wrong label.

### Narrative Registry Schema V2

Each active reviewed narrative should carry language-explicit fields:

- `narrative_id`
- `canonical_name_zh`
- `canonical_name_en`
- `display_name`
- `canonical_taxonomy_zh`
- `canonical_taxonomy_en`
- `parent_id`
- `level`
- `status`
- `aliases_zh`
- `aliases_en`
- `related_terms_zh`
- `related_terms_en`
- `definition_zh`
- `definition_en`
- `inclusion_criteria_zh`
- `exclusion_criteria_zh`
- `representative_stocks`
- `review_metadata`

Rules:

- `display_name` defaults to `canonical_name_zh`
- English names must never be the only canonical label
- old `name`, `aliases`, and `related_terms` fields should be preserved only as
  migration compatibility fields until all readers are upgraded

### Mapping Model V2

Replace the current direct `stock -> narrative` mental model with a two-step
model:

1. `stock -> company_exposure_tags`
   - stable business or chain labels
   - may be multi-label

2. `company_exposure_tags -> narrative`
   - fund-level narrative assembled from repeated tag concentration plus
     evidence support

This change is necessary because funds such as `515880` are not best described
by a direct jump from one stock name or one industry field to one broad
registry narrative.

Example shape:

- `新易盛 -> 高速光模块`
- `中际旭创 -> 高速光模块`
- `天孚通信 -> 光器件`
- `中兴通讯 -> 通信设备`
- `中天科技 -> 光通信/海缆基础设施`

Then the service can aggregate these tags into a candidate narrative such as
`AI光互联基础设施`, rather than forcing everything into
`Semiconductor Capex Cycle`.

### Source Normalization V2

The source catalog should produce Chinese-first semantic objects instead of raw
token bags.

For each `source_item`, preserve:

- `source_item_id`
- `source_type`
- `provider_name`
- `source_url`
- `stock_code`
- `stock_name_zh`
- `stock_name_en`
- `event_date`
- `headline_zh`
- `headline_en`
- `summary_zh`
- `summary_en`
- `fact_type`
- `fact_direction`
- `fact_confidence`
- `company_keywords_zh`
- `company_keywords_en`
- `event_keywords_zh`
- `event_keywords_en`

Do not let templated provider strings dominate the semantic layer. Quote and
valuation snapshots should enrich state scoring, but they should not become the
primary term source for narrative naming.

### Candidate Generation V2

Candidate generation should no longer start from repeated token frequency alone.

Use three stages:

1. `fact extraction`
   - classify each source item into a company fact
   - examples: order, capacity expansion, price cut, earnings decline,
     guidance raise, valuation compression

2. `cross-company clustering`
   - group company facts that share:
     - business chain
     - event type
     - repeated Chinese keywords
     - recurring representative stocks

3. `narrative abstraction`
   - let the LLM propose a Chinese narrative only after a cluster is formed

Hard quality gates:

- a single-stock cluster is not enough by default
- a company name or province name cannot become the narrative name
- quote-only or valuation-only clusters cannot become narratives
- a candidate must explain why it is not just one company event

### LLM Responsibility V2

The LLM should do only the semantic work that deterministic code cannot do
reliably.

Allowed:

- cluster naming in Chinese
- Chinese definition writing
- alias and related-term expansion
- narrative merge / split judgment
- stock exposure explanation
- conflict explanation between positive and negative evidence

Not allowed:

- inventing facts, URLs, dates, metrics, or cited items
- deciding final approval
- directly writing reviewed registry or reviewed mapping stores

Required output schema for candidate narrative curation:

- `canonical_name_zh`
- `canonical_name_en`
- `canonical_taxonomy_zh`
- `canonical_taxonomy_en`
- `definition_zh`
- `aliases_zh`
- `aliases_en`
- `related_terms_zh`
- `related_terms_en`
- `inclusion_criteria_zh`
- `exclusion_criteria_zh`
- `why_not_company_event_zh`
- `representative_citation_ids`
- `representative_stock_codes`
- `confidence`

Prompt rules:

- instruct the model that the domain is China A-share funds
- require Chinese output for all narrative-facing text
- explicitly forbid company names or province names as stand-alone narrative
  names
- explicitly state that English is alias-only

### Review Workflow V2

Human review should evaluate structured Chinese proposals, not decode noisy raw
candidates.

Each review item should show:

- `proposed_canonical_name_zh`
- `proposed_parent_narrative`
- `definition_zh`
- `core_stock_codes`
- `core_stock_names`
- `supporting_company_facts`
- `supporting_citations`
- `counter_evidence`
- `why_not_company_event_zh`
- `mapping_impact_preview`
- `merge_with_existing_narrative`
- `available_actions`

Actions remain:

- `approve`
- `reject`
- `defer`

But `approve` should optionally support:

- create new narrative
- merge into existing narrative
- rename an existing narrative while preserving id continuity

### Runtime Cadence V2

Use separate clocks for different layers:

1. daily or event-driven
   - holdings refresh
   - quotes
   - valuation
   - financial metrics
   - evidence refresh
   - state scoring only

2. weekly
   - company fact refresh
   - exposure-tag refresh
   - candidate narrative generation
   - mapping proposal generation

3. human-reviewed promotion
   - reviewed registry updates
   - reviewed mapping updates

### Migration Plan

Implement V2 in this order:

1. `registry-localization`
   - add Chinese-first registry fields
   - stop report rendering from using English `name` as primary display

2. `semantic-object-split`
   - add `company_fact` and `company_exposure_tag` working objects
   - keep compatibility with current raw/scoring outputs

3. `source-normalization-v2`
   - rewrite source term extraction to emit Chinese-first fact metadata

4. `mapping-v2`
   - add `stock -> exposure_tag` layer
   - add fund-level `exposure_tag -> narrative` aggregation

5. `candidate-curation-v2`
   - replace token-frequency-first candidate generation with cluster-based
     candidate generation

6. `review-queue-v2`
   - upgrade review queue payload to carry Chinese-first proposal fields and
     merge/rename actions

7. `report-display-v2`
   - ensure reports expose Chinese narrative names and Chinese review context

8. `acceptance-v2`
   - require Chinese canonical names in reviewed registry
   - reject English-only active narrative entries
   - require representative multi-stock or multi-fact support for new
     narratives

### Acceptance Criteria

V2 should not be called complete unless all of the following are true:

1. default report display for A-share funds is Chinese-first
2. no active reviewed narrative is English-only
3. single-stock quote-only events do not create narrative candidates
4. funds like `161725` and `515880` can be explained through reviewed Chinese
   narratives without broad-industry fallback dominating the result
5. review queue items are intelligible to a human reviewer without reading raw
   provider payloads
6. provider-foundation disclosure still makes mock versus reviewed versus
   derived layers explicit

## Narrative V2 Execution Knives

Use this as the implementation order for the V2 redesign.

1. `registry-compat-layer`
   - add normalized Chinese-first registry and candidate compatibility fields
   - keep old `name` and `canonical_taxonomy` fields readable during migration
   - status: implemented on 2026-05-15

2. `display-path-switch`
   - switch aggregation, diagnostics, review queue, and report rendering to use
     Chinese display names when available
   - status: implemented on 2026-05-15

3. `review-promotion-compat`
   - keep review queue and promotion flows compatible while writing V2-friendly
     fields on promoted narratives
   - status: implemented on 2026-05-15

4. `regression-rebaseline`
   - update tests for Chinese-first display and compatibility fields
   - status: implemented on 2026-05-15

5. `candidate-zh-contract`
   - require generated candidates to emit explicit Chinese display and
     explanation fields
   - status: pending

6. `reviewed-store-migration`
   - rewrite reviewed registry entries so Chinese canonical names live in the
     durable store itself, not only in compatibility helpers
   - status: pending

7. `company-fact-layer`
   - introduce `company_fact` objects as a first-class working layer
   - status: implemented on 2026-05-15

8. `company-exposure-tags`
   - introduce `stock -> company_exposure_tag` derivation and persistence
   - status: implemented on 2026-05-15

9. `mapping-v2-aggregation`
   - aggregate fund exposure through exposure tags before mapping into
     narratives
   - status: implemented on 2026-05-15

10. `candidate-cluster-curation`
   - replace token-frequency-first generation with cross-company cluster-based
     Chinese narrative abstraction
   - status: implemented on 2026-05-15

11. `review-queue-v2`
    - extend review payloads with Chinese proposal fields, merge targets, and
      company-fact evidence summaries
    - status: pending

12. `acceptance-v2`
    - enforce Chinese-first reviewed registry and reject English-only active
      narratives in the acceptance lane
    - status: pending
