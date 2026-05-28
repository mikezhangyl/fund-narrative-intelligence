# Task Handoff

MIK-44 defined the trusted promotion transaction boundary without enabling promotion execution.

## Delivered

- Added `promotion_transaction_boundary` to `config/narrative_service_contract.yaml`.
- Reserved `POST /api/v1/narratives/promotion/commit` as the future command surface.
- Declared required command fields, prerequisites, all-or-none write set, rollback/failure behavior, and promotion audit record schema.
- Added reserved `promotion_decisions_path` to `ServiceConfig`, CLI wiring, and deterministic acceptance setup.
- Added a test proving intake, review action, and preflight cannot create trusted records or promotion decision records.
- Updated runbook and startup memory.

## Verification

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_narrative_review_workspace.py tests/test_trust_state_disclosure.py tests/test_mapping_evidence_pack_report.py tests/test_fund_holding_exposure_report.py -q`
- `uv run --extra dev ruff check config scripts/validate_stock_narrative_service_acceptance.py services/stock-narrative-service/src/stock_narrative_service/config.py services/stock-narrative-service/src/stock_narrative_service/main.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`

All checks passed.
