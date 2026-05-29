# Narrative Radar Service Boundary And Source-Signal Model - 2026-05-29

Canonical readable artifact:
`docs/product/narrative-radar-service-boundary-and-model-2026-05-29.html`

## Linear Scope

- `MIK-80`: Narrative Radar ownership and service API boundary.
- `MIK-81`: Radar score schema and explainability contract.
- `MIK-82`: Radar source-signal time-series model.

## Decision

Narrative Radar is owned by Narrative Service.

FNI may consume radar HTTP responses in later report or preview surfaces, but it
must not mine source events, calculate radar scores, infer trend state, or mutate
candidate/trusted narrative state. Gateway remains the owner of external
provider access and normalized provider contracts.

## Implemented Service Contract

The service now exposes:

- `GET /api/v1/narratives/radar/contract`
- `GET /api/v1/narratives/radar/signals`

Both endpoints use the existing Narrative Service envelope with:

- `status`
- `source`
- `provider`
- `provider_version`
- `data`
- `warnings`
- `diagnostics`
- `trust_metadata`

## Score Schema

The radar contract declares deterministic score ownership with formula version
`radar-deterministic-v0`.

Required score fields:

- `heat_score`
- `trend_score`
- `momentum_state`
- `market_confirmation_score`
- `evidence_quality_score`
- `source_attention_components`
- `window_start`
- `window_end`
- `baseline_window`
- `formula_version`
- `degradation_warnings`

AI summaries may explain evidence in a later slice, but they cannot override
deterministic scores.

## Time-Series Model

`GET /api/v1/narratives/radar/signals` replays seed and intake events into
append-only radar source signals without writing negative cache records for
failed upstream/provider attempts.

Each signal includes:

- source event identity and source type
- candidate narrative identity
- extracted tickers, sectors, concepts, and keywords
- event and ingestion timestamps
- signal strength and source weight
- evidence references
- provider/source metadata

The first aggregation surface emits daily window snapshots. The public model
declares both hourly and daily granularity so later scoring can add hourly
windows without changing the API shape.

## Verification

- RED:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q`
  failed on missing radar endpoints.
- GREEN:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q`
  passed with 31 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service/radar.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/src/stock_narrative_service/app.py services/stock-narrative-service/tests/test_http_service.py`
  passed.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
