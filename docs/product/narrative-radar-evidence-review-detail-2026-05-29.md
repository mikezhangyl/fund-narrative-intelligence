# Narrative Radar Evidence And Review Detail - 2026-05-29

Canonical readable artifact:
`docs/product/narrative-radar-evidence-review-detail-2026-05-29.html`

## Linear Scope

- `MIK-77`: Radar drill-down from bubble to evidence and review state.
- `MIK-85`: Radar state and review integration.

## Implemented Service Contract

Narrative Service now exposes:

```text
GET /api/v1/narratives/radar/evidence?narrative_id=<id>
```

Bubble rows also expose a stable `detail_path` pointing to this endpoint.

## Detail Payload

The detail payload includes:

- linked candidate record identity
- trust status
- radar state
- latest review state and review action identifiers
- representative stocks
- extracted entities
- source evidence references
- score components
- degradation warnings
- historical interpretation after review state changes

## Review / Trust States

The radar detail model exposes these service-owned states:

- `candidate`
- `reviewed`
- `trusted`
- `rejected`
- `deprecated`

Current review integration maps no action to `candidate`, approval to
`reviewed`, and rejection to `rejected`. Trusted promotion remains a separate
service governance action; radar detail does not promote candidates.

## Verification

- RED:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_bubbles_return_visualization_ready_contract_without_recalculation services/stock-narrative-service/tests/test_http_service.py::test_radar_evidence_detail_tracks_review_state_transitions -q`
  failed on missing `detail_path` and missing evidence endpoint.
- GREEN:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 40 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service/radar.py services/stock-narrative-service/src/stock_narrative_service/app.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py`
  passed.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
