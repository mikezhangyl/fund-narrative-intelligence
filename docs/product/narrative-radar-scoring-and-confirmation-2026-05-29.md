# Narrative Radar Scoring And Market Confirmation - 2026-05-29

Canonical readable artifact:
`docs/product/narrative-radar-scoring-and-confirmation-2026-05-29.html`

## Linear Scope

- `MIK-75`: Narrative heat and trend scoring.
- `MIK-83`: Market confirmation adapter boundary.

## Implemented Service Contract

Narrative Service now exposes:

```text
GET /api/v1/narratives/radar/scores
```

Supported query fields:

- `as_of`
- `window_days`
- `baseline_days`
- `half_life_hours`

The endpoint returns deterministic scores with formula version
`radar-deterministic-v0`.

## Deterministic Score Output

Each score includes:

- `heat_score`
- `trend_score`
- `trend_acceleration`
- `momentum_state`
- `market_confirmation_score`
- `evidence_quality_score`
- `source_attention_components`
- `window_start`
- `window_end`
- `baseline_window`
- `formula_version`
- `degradation_warnings`

The current implementation scores source attention from replayed radar source
signals. Recency decay is configurable through `half_life_hours`; short-window
attention is compared with a longer baseline window. Sustained rise across
windows is marked as `heating`, while strong source evidence without prior
baseline is marked as `emerging`.

## Market Confirmation Boundary

Market confirmation is implemented as a mockable local contract adapter. The
adapter reads normalized confirmation records from
`ServiceConfig.market_confirmation_path`.

Boundary rules:

- Gateway remains owner of raw market/provider access.
- Narrative Service consumes normalized confirmation inputs only.
- No Tushare, AkShare, EastMoney, or direct external provider integration is
  introduced in radar scoring.
- Missing market confirmation produces degraded metadata but does not suppress
  source-driven heat.

## Verification

- RED:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q`
  failed on missing scoring endpoint/config behavior.
- GREEN:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_scores_are_deterministic_and_mark_sustained_heating services/stock-narrative-service/tests/test_http_service.py::test_radar_scores_degrade_market_confirmation_without_suppressing_source_heat -q`
  passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 35 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`
  passed.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
