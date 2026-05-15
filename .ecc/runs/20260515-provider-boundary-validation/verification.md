# Verification

- RED: `python -m pytest tests/test_cli_pipeline.py::test_optional_market_quotes_rejects_malformed_provider_payload tests/test_cli_pipeline.py::test_optional_news_evidence_rejects_malformed_provider_payload -q`
  - Result: failed as expected; market payload was not rejected and news failed later with `AttributeError`.
- GREEN target: `python -m pytest tests/test_cli_pipeline.py::test_optional_market_quotes_rejects_malformed_provider_payload tests/test_cli_pipeline.py::test_optional_news_evidence_rejects_malformed_provider_payload -q`
  - Result: 2 passed.
- Related tests: `python -m pytest tests/test_cli_pipeline.py tests/test_workspace_snapshot.py -q`
  - Result: 69 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 267 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed.
