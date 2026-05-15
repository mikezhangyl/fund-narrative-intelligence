# Verification

- RED: `python -m pytest tests/test_cli_pipeline.py::test_artifact_contracts_reject_invalid_market_quotes_payload tests/test_cli_pipeline.py::test_artifact_contracts_reject_invalid_announcement_evidence_payload -q`
  - Result: failed as expected because artifact contracts did not validate those optional payloads.
- GREEN target: `python -m pytest tests/test_cli_pipeline.py::test_artifact_contracts_reject_invalid_market_quotes_payload tests/test_cli_pipeline.py::test_artifact_contracts_reject_invalid_announcement_evidence_payload -q`
  - Result: 2 passed.
- Related tests: `python -m pytest tests/test_cli_pipeline.py -q`
  - Result: 56 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 271 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed.
