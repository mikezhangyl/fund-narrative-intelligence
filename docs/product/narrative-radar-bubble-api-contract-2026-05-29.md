# Narrative Radar Bubble API Contract - 2026-05-29

Canonical readable artifact:
`docs/product/narrative-radar-bubble-api-contract-2026-05-29.html`

## Linear Scope

- `MIK-74`: Narrative Radar bubble data API.
- `MIK-84`: Bubble chart data contract.

## Implemented Service Contract

Narrative Service now exposes:

```text
GET /api/v1/narratives/radar/bubbles
```

The endpoint returns service-owned, library-agnostic JSON data suitable for a
bubble visualization. It is not a fund report endpoint and does not require FNI
to recalculate scores.

## Bubble Row Fields

Each bubble row includes:

- `narrative_id`
- `narrative_name`
- `heat_score`
- `trend_score`
- `trend_acceleration`
- `momentum_state`
- `market_confirmation_score`
- `trust_status`
- `evidence_quality_score`
- `source_count`
- `representative_stocks`
- `window_metrics`
- `sparkline_points`
- `evidence_refs`
- `score_components`
- `degradation_warnings`
- `updated_at`
- `visual_encoding`

## Visualization Mapping

The response includes `visualization_contract.version=bubble-chart-contract-v1`.

Mapping:

- bubble size: `heat_score`
- x: `trend_acceleration`
- y: `market_confirmation_score`
- color: `momentum_state`
- border: `trust_status`
- marker: `evidence_quality_score`
- tooltip: evidence refs, representative stocks, source count, score components,
  sparkline, and degradation warnings

## Degraded / Empty Inputs

Empty source inputs return a structured `RADAR_BUBBLES_EMPTY` product-data-gap
warning with an empty bubble list and the visualization contract still present.

## Verification

- RED:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_bubbles_return_visualization_ready_contract_without_recalculation services/stock-narrative-service/tests/test_http_service.py::test_radar_bubbles_empty_inputs_return_structured_metadata -q`
  failed on missing bubble endpoint.
- GREEN:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 39 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service/radar.py services/stock-narrative-service/src/stock_narrative_service/app.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py`
  passed.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
