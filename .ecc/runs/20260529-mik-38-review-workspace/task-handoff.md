# Task Handoff

## Goal

MIK-38: provide a CLI/HTML human review workspace so reviewers can process
candidate narratives without reading raw JSON.

## Files Changed

- `docs/memory/current-brief.md`
- `docs/product/stock-narrative-service-runbook.md`
- `scripts/run_narrative_review_workspace.py`
- `tests/test_narrative_review_workspace.py`

## Implementation Summary

Added `scripts/run_narrative_review_workspace.py`. It can fetch review queue,
candidate details, and evidence pack links from a running Narrative Service,
group candidates by review status, show missing gates and recommended actions,
write JSON plus Chinese HTML, and optionally submit `approve`, `reject`, or
`defer` through the service review-action endpoint before rendering.

## Commands Run

- `uv run pytest tests/test_narrative_review_workspace.py -q`
- `uv run pytest tests/test_narrative_review_workspace.py services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py tests/test_narrative_service_provider.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_mapping_evidence_pack_report.py -q`
- `uv run --extra dev ruff check scripts/run_narrative_review_workspace.py tests/test_narrative_review_workspace.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`
- `PYTHONPATH=services/stock-narrative-service/src uv run python - <<'PY' ...`

## Test Results

- New review workspace tests: 3 passed.
- Combined related suite: 46 passed.
- Generated workspace acceptance artifact:
  `outputs/narrative_review_workspace/2026-05-28T1744Z/`.
- Ruff, compileall, and diff whitespace checks passed.

## Known Risks And Assumptions

- This is CLI/HTML first, not a persistent browser app.
- The generated HTML links to service endpoints; reviewers need a running service
  for live detail pages.
- The script submits actions only when explicit action arguments are provided.

## Suggested Quality Checks

- MIK-40 should make intake metadata visible through queue/detail records so the
  workspace can surface provider and permission state.
- Future web UI can reuse the JSON workspace shape as a first view model.
