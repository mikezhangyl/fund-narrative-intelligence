# Narrative Radar Preview And Explanation Contract - 2026-05-29

Canonical readable artifact:
`docs/product/narrative-radar-preview-and-explanation-contract-2026-05-29.html`

## Linear Scope

- `MIK-78`: Narrative Radar service preview surface.
- `MIK-79`: AI narrative explanation as optional evidence summary.

## Preview Surface

Narrative Service now exposes:

```text
GET /api/v1/narratives/radar/preview
```

This is a service/dev preview payload, not an investment report and not an FNI
fund workflow. The payload reuses `GET /api/v1/narratives/radar/bubbles` data
and does not recalculate radar scores client-side.

Preview metadata includes:

- surface type `service_dev_preview`
- `not_report_product=true`
- `score_recalculation=none`
- responsive layout contract
- visualization contract from the bubble API
- render model with bubbles, legend, and interaction hints

## Optional Explanation Contract

Radar evidence detail now accepts:

```text
GET /api/v1/narratives/radar/evidence?narrative_id=<id>&include_explanation=true
```

Explanation is disabled by default. When enabled, the summary is explicitly
non-authoritative:

- `authoritative=false`
- `score_effect=none`
- `trust_effect=none`
- evidence references are included
- deterministic scores and trust state remain unchanged

No AI prediction, AI-only narrative creation, or AI-based trusted promotion is
introduced.

## Verification

- RED:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_preview_surface_uses_bubble_api_contract_without_report_semantics services/stock-narrative-service/tests/test_http_service.py::test_radar_evidence_optional_explanation_is_disabled_by_default_and_non_authoritative -q`
  failed on missing preview endpoint and missing explanation contract.
- GREEN:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 42 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`
  passed.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
