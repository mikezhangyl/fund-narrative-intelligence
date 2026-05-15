# Verification

- RED: `python -m pytest tests/test_cli_pipeline.py::test_artifact_contracts_reject_optional_payload_drift -q`
  - Result: failed as expected because artifact contracts did not compare raw/scoring optional payloads.
- GREEN target: `python -m pytest tests/test_cli_pipeline.py::test_artifact_contracts_reject_optional_payload_drift -q`
  - Result: 1 passed.
- Related tests: `python -m pytest tests/test_cli_pipeline.py -q`
  - Result: 57 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 272 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed.
