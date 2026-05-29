# Narrative Radar Service Plan - 2026-05-29

## Decision

Narrative Radar is part of Narrative Service.

It is not a report feature, not a fund-analysis feature, and not a layer where FNI should calculate narrative scores. FNI may later consume and render radar data, but Narrative Service owns source intake, candidate narrative mining, scoring, trend state, trust state, and radar API output.

## Capability

Users can view the current market from a narrative-first perspective:

- Large bubbles represent narratives with high current heat.
- Small bubbles represent narratives with lower current attention.
- Heating narratives are visually distinguishable from stable or cooling narratives.
- Every bubble can be traced back to source evidence and review status.
- Untrusted mined narratives remain visibly marked as candidates until reviewed.

## Product Scenarios

### Scenario 1: See Current Mainstream Narratives

As a market narrative analyst, I want to see which narratives are currently dominant, so I can understand what themes are driving market attention before entering fund or stock-level analysis.

Required service output:

- narrative identity
- heat score
- representative stocks
- source count
- evidence quality
- trust status

### Scenario 2: Detect Heating Narratives

As a market narrative analyst, I want to see narratives that are continuously heating up, not only narratives that are already large, so I can detect trend emergence early.

Required service output:

- trend score
- momentum state: `emerging`, `heating`, `stable`, `cooling`
- short-window vs baseline-window metrics
- sparkline points
- formula version

### Scenario 3: Drill Into Evidence

As a reviewer, I want to click a radar bubble and see why the service believes this narrative exists, so I can decide whether it is credible.

Required service output:

- source evidence references
- source type
- extracted entities
- linked candidate or trusted narrative record
- review state
- score component breakdown

### Scenario 4: Keep Report And Fund Layers Clean

As an architect, I want radar logic to stay inside Narrative Service, so downstream reports and fund workflows can consume stable service contracts without duplicating mining or scoring logic.

Required boundary:

- FNI may render or reference radar data.
- FNI must not recompute radar scores.
- Gateway owns raw provider access.
- Narrative Service consumes normalized source events and market confirmation inputs through contracts.

## Bubble Data Contract

The first radar API should return library-agnostic JSON data. Rendering clients should be able to build a bubble chart without scoring logic.

Core fields:

- `narrative_id`
- `narrative_name`
- `heat_score`
- `trend_score`
- `trend_acceleration`
- `momentum_state`
- `market_confirmation_score`
- `evidence_quality_score`
- `trust_status`
- `source_count`
- `representative_stocks`
- `window_metrics`
- `sparkline_points`
- `evidence_refs`
- `score_components`
- `degradation_warnings`
- `updated_at`

Recommended visual mapping:

- bubble size: `heat_score`
- x axis: `trend_acceleration` or `trend_score`
- y axis: `market_confirmation_score`
- color: `momentum_state`
- border or marker: `trust_status` and `evidence_quality_score`
- hover: evidence summary, representative stocks, source count, sparkline, score components

## Narrative Mining Method

The Can-Do version should mine from structured sources first. It should not scrape social media or browser-only websites.

Initial inputs:

- gateway-backed Tushare news briefs when available
- announcement and disclosure-style source events
- existing reviewed narrative seeds as anchors
- market structure signals only as confirmation, not as source text

Mining steps:

1. Normalize source events into a shared event schema.
2. Extract entities such as tickers, sectors, concepts, organizations, keywords, and event topics.
3. Group events by co-occurrence and semantic anchors.
4. Create or update candidate narrative signals.
5. Attach evidence references and source metadata.
6. Score attention, trend, market confirmation, and evidence quality.
7. Expose radar rows with candidate/trusted state clearly marked.

## Scoring Model

Scoring should be deterministic first. AI may later summarize evidence, but it must not decide heat, trend, trust, or prediction.

Required components:

- `heat_score`: weighted current attention over a recent window
- `trend_score`: short-window heat compared with longer baseline heat
- `trend_acceleration`: rate of change across windows
- `market_confirmation_score`: optional market behavior confirmation from gateway/FNI contracts
- `evidence_quality_score`: confidence based on source mix, mapping quality, and review state
- `momentum_state`: derived from score direction and persistence

Every score should expose:

- formula version
- window start and end
- baseline window
- component weights
- degraded-source warnings

## Architecture Boundaries

### Narrative Service Owns

- radar source-event ingestion
- candidate narrative mining
- narrative heat and trend scoring
- radar time-series storage
- radar API
- review and trust state integration
- evidence linkage

### Gateway Owns

- external provider access
- raw market/news/fundamental provider normalization
- provider fallback and timeout behavior
- source availability and degraded metadata

### FNI Owns

- future consumption of radar API
- downstream display or report references
- fund workflow integration after Narrative Service exposes stable contracts

FNI must not own radar scoring or candidate mining.

## Linear Execution Plan

### PM Parent

- MIK-68: `[PM-R3] Product requirement pack for Narrative Radar Service`

### PM Child Issues

- MIK-74: `[P0][PM-R3] Narrative Radar bubble data API`
- MIK-75: `[P0][PM-R3] Narrative heat and trend scoring`
- MIK-76: `[P0][PM-R3] Structured source mining into candidate narratives`
- MIK-77: `[P1][PM-R3] Radar drill-down from bubble to evidence and review state`
- MIK-78: `[P1][PM-R3] Narrative Radar service preview surface`
- MIK-79: `[P2][PM-R3] AI narrative explanation as optional evidence summary`

### Architect Parent

- MIK-69: `[ARCH-R3] Architecture requirement pack for Narrative Radar Service`

### Architect Child Issues

- MIK-80: `[ARCH-P0][R3] Narrative Radar ownership and service API boundary`
- MIK-81: `[ARCH-P0][R3] Radar score schema and explainability contract`
- MIK-82: `[ARCH-P0][R3] Radar source-signal time-series model`
- MIK-83: `[ARCH-P1][R3] Market confirmation adapter boundary`
- MIK-84: `[ARCH-P1][R3] Bubble chart data contract`
- MIK-85: `[ARCH-P1][R3] Radar state and review integration`

## Recommended Developer Order

1. MIK-80 + MIK-81 + MIK-82: fix ownership, schema, and time-series model.
2. MIK-75: implement deterministic heat and trend scoring with replayable fixtures.
3. MIK-76: implement structured source mining into candidate narrative signals.
4. MIK-74 + MIK-84: expose radar bubble API contract.
5. MIK-77 + MIK-85: connect radar rows to evidence and review state.
6. MIK-78: add a service-owned preview surface only after the API is stable.
7. MIK-79: add optional AI explanation only after evidence and scoring are deterministic.

## Non-Goals

- No AI prediction.
- No report generation.
- No fund report logic.
- No social scraping.
- No Snowball, Taoguba, X/Twitter, Reddit scraping.
- No browser automation.
- No proxy or anti-detect infrastructure.
- No automatic trust promotion from AI output.

## Acceptance Gate

This milestone is accepted when Narrative Service can produce reproducible radar rows from deterministic source fixtures, expose score components and trust state, and provide enough data for a bubble chart without moving radar logic into FNI reports or fund-analysis code.
