# Financial Metrics Report Verification

Status: passed

Commands:

- `python -m pytest tests/test_report_writer.py::test_html_report_renders_structured_sections_without_raw_markdown tests/test_cli_pipeline.py::test_optional_financial_metrics_produce_earnings_signals -q`
  - Result: red first, then passed after implementation
- `python -m pytest tests/test_report_writer.py tests/test_cli_pipeline.py::test_optional_financial_metrics_produce_earnings_signals tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: passed, `5 passed in 0.07s`
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed
- `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: passed, `257 passed`, total coverage `80%`
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed; reports include `Financial Metrics` and `eastmoney-financial-metrics`
