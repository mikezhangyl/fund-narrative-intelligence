# Eastmoney Valuation Provider Verification

Status: passed

Commands:

- `python -m pytest tests/test_eastmoney_valuation_provider.py tests/test_cli_pipeline.py::test_optional_valuation_snapshots_can_use_eastmoney_metrics tests/test_cli_pipeline.py::test_optional_valuation_snapshots_are_quote_derived_and_disclosed tests/test_cli_pipeline.py::test_cli_eastmoney_valuation_source_does_not_require_market_quotes tests/test_cli_pipeline.py::test_cli_include_valuation_snapshots_passes_option_to_pipeline tests/test_cli_pipeline.py::test_cli_include_valuation_snapshots_requires_market_quotes tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: 11 passed
- `python -m ruff check src/providers/eastmoney_valuation.py src/orchestrator.py src/main.py src/validation.py src/modules/valuation/snapshots.py src/modules/workspace_snapshot/builder.py scripts/validate_reviewed_mapping_enriched_acceptance.py tests/test_eastmoney_valuation_provider.py tests/test_cli_pipeline.py tests/test_reviewed_mapping_enriched_acceptance_script.py`
  - Result: passed
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725`
  - Result: first attempt exposed CNINFO timeout with valuation fresh; retry passed with `valuation=eastmoney` and workspace snapshot valid
- `python -m pytest tests/test_eastmoney_valuation_provider.py tests/test_cli_pipeline.py::test_optional_valuation_snapshots_can_use_eastmoney_metrics tests/test_cli_pipeline.py::test_optional_valuation_snapshots_are_quote_derived_and_disclosed tests/test_cli_pipeline.py::test_cli_eastmoney_valuation_source_does_not_require_market_quotes tests/test_cli_pipeline.py::test_cli_include_valuation_snapshots_passes_option_to_pipeline tests/test_cli_pipeline.py::test_cli_include_valuation_snapshots_requires_market_quotes tests/test_reviewed_mapping_enriched_acceptance_script.py tests/test_workspace_snapshot.py -q`
  - Result: 22 passed
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed; built and validated `fund_000001_workspace_snapshot.json`
- `python -m coverage run -m pytest && python -m coverage report`
  - Result: 243 passed; total coverage 80%
