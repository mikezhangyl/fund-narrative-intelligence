# Task Handoff

MIK-39 implemented the explicit trusted promotion workflow.

## Delivered

- Added `POST /api/v1/narratives/promotion/commit`.
- Failed gates return structured `PROMOTION_GATES_MISSING` with exact `missing_gates` and no writes.
- Successful promotion requires evidence, rationale, exclusions, approve review action, and `trust_audit_result=passed`.
- Successful promotion writes trusted registry, trusted mapping, trusted evidence pack, and append-only `PD_*` promotion decision ledger records as one rollback-protected transaction.
- Contract and runbook now mark the promotion commit surface as enabled.

## Verification

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_narrative_review_workspace.py tests/test_trust_state_disclosure.py tests/test_mapping_evidence_pack_report.py tests/test_fund_holding_exposure_report.py tests/test_narrative_service_provider.py -q`
- `uv run --extra dev ruff check config scripts/validate_stock_narrative_service_acceptance.py services/stock-narrative-service/src/stock_narrative_service/app.py services/stock-narrative-service/src/stock_narrative_service/config.py services/stock-narrative-service/src/stock_narrative_service/main.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`

All checks passed.
