# Eastmoney Financial Metrics Verification

Status: passed

Commands:

- `python -m pytest tests/test_eastmoney_financial_metrics_provider.py tests/test_derived_signals.py::test_derives_earnings_signal_from_positive_financial_metrics -q` - passed, 4 tests.
- `python -m pytest tests/test_cli_pipeline.py::test_optional_financial_metrics_produce_earnings_signals -q` - passed, 1 test.
- `python -m pytest tests/test_reviewed_mapping_enriched_acceptance_script.py tests/test_eastmoney_financial_metrics_provider.py tests/test_derived_signals.py::test_derives_earnings_signal_from_positive_financial_metrics tests/test_cli_pipeline.py::test_optional_financial_metrics_produce_earnings_signals tests/test_cli_pipeline.py::test_cli_include_financial_metrics_passes_option_to_pipeline -q` - passed, 9 tests.
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance` - passed with `financial_metrics=eastmoney`.
- `python -m ruff check .` - passed.
- `python -m compileall -q src tests scripts` - passed.
- `python -m coverage run -m pytest -q && python -m coverage report` - passed, 255 tests, total coverage 80%.
- `python scripts/validate_v1_acceptance.py` - passed.

Acceptance evidence:

- Reviewed-mapping enriched acceptance generated `financial_metrics` with provider `eastmoney-financial-metrics`.
- Provider foundation includes a non-mock `financial_metrics` layer.
- Signal trace includes financial-derived `revenue_growth_up` signals from `financial_metrics`.
