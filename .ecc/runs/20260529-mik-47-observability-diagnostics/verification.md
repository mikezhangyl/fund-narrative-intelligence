# Verification

TDD red:

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_ops_summary_includes_operational_diagnostics services/stock-narrative-service/tests/test_http_service.py::test_runtime_failure_returns_classified_diagnostics_warning tests/test_narrative_service_conformance_probe.py::test_narrative_service_contract_declares_observability_policy -q`
- Result before implementation: 3 failed as expected.

Green checks:

- `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_ops_summary_includes_operational_diagnostics services/stock-narrative-service/tests/test_http_service.py::test_runtime_failure_returns_classified_diagnostics_warning tests/test_narrative_service_conformance_probe.py::test_narrative_service_contract_declares_observability_policy -q` -> 3 passed.
- `uv run pytest services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py -q` -> 41 passed.
- `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py tests/test_narrative_service_conformance_probe.py` -> passed.
- `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests tests scripts` -> passed.
- `git diff --check` -> passed.
- `uv run python scripts/validate_stock_narrative_service_acceptance.py` -> completed; endpoint_count=13, provider_smoke_source=narrative_service, report_status=completed.
