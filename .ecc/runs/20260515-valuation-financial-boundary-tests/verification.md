# Verification

- Target: `python -m pytest tests/test_cli_pipeline.py::test_optional_valuation_snapshots_rejects_malformed_provider_payload tests/test_cli_pipeline.py::test_optional_financial_metrics_rejects_malformed_provider_payload -q`
  - Result: 2 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 269 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed.
