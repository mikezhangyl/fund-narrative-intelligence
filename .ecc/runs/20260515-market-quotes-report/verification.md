# Market Quotes Report Verification

Status: passed

Commands:

- `python -m pytest tests/test_report_writer.py::test_html_report_renders_structured_sections_without_raw_markdown tests/test_cli_pipeline.py::test_optional_eastmoney_quotes_are_disclosed_and_added_to_outputs -q`
  - Result: red first, then passed after implementation
- `python -m ruff check src/modules/report_writer/writer.py tests/test_report_writer.py tests/test_cli_pipeline.py`
  - Result: passed
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed
- `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: passed, `259 passed`, total coverage `80%`
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed; report includes market quote section in live enriched path
