# Verification

TDD red:

- `uv run pytest tests/test_stock_narrative_service_acceptance.py tests/test_narrative_service_conformance_probe.py::test_narrative_service_conformance_probe_checks_contract_endpoints tests/test_ci_workflow.py -q`
- Result before implementation: acceptance summary lacked fallback smoke/CI gate metadata; CI workflow lacked the Stock Narrative Service gate.

Green checks:

- `uv run pytest tests/test_stock_narrative_service_acceptance.py tests/test_narrative_service_conformance_probe.py::test_narrative_service_conformance_probe_checks_contract_endpoints tests/test_ci_workflow.py -q` -> 3 passed.
- `uv run pytest tests/test_stock_narrative_service_acceptance.py tests/test_narrative_service_conformance_probe.py tests/test_narrative_service_provider_smoke.py tests/test_narrative_service_provider.py tests/test_ci_workflow.py -q` -> 24 passed.
- `uv run ruff check scripts/validate_stock_narrative_service_acceptance.py tests/test_stock_narrative_service_acceptance.py tests/test_narrative_service_conformance_probe.py tests/test_ci_workflow.py` -> passed.
- `uv run python -m compileall -q scripts tests services/stock-narrative-service/src` -> passed.
- `git diff --check` -> passed.
- `uv run python scripts/validate_stock_narrative_service_acceptance.py` -> completed; provider_smoke_source=narrative_service, fallback_smoke_source=local_prototype, report_status=completed.
- `uv run pytest -q` -> 514 passed, 1 skipped.
