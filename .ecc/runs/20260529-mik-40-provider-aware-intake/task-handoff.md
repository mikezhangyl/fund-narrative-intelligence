# Task Handoff

MIK-40 implemented provider-aware narrative intake for the in-repo Narrative Service.

## Delivered

- `news`, `announcement`, `manual`, and `social_future` intake events normalize provider/source metadata.
- News and announcement policy prefers gateway/Tushare structured sources before public website crawling.
- Intake responses include `evidence_reinforcements` for existing narrative ids.
- Candidate outputs and reinforcements remain `candidate_untrusted` with `promotion_effect=none`.
- Runbook, contract, and startup memory now describe the intake policy.

## Verification

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py tests/test_narrative_review_workspace.py tests/test_narrative_service_provider.py tests/test_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_script.py tests/test_mapping_evidence_pack_report.py -q`
- `uv run --extra dev ruff check config tests/test_narrative_service_conformance_probe.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py`
- `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
- `git diff --check`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`

All checks passed.
