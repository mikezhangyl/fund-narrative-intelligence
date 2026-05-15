# Verification

- RED: `python -m pytest tests/test_cli_pipeline.py::test_optional_announcement_evidence_rejects_malformed_provider_payload tests/test_announcement_evidence.py::test_converts_supporting_cninfo_announcement_to_mapped_evidence -q`
  - Result: failed as expected because `validate_announcement_evidence_payload` did not exist yet.
- GREEN target: `python -m pytest tests/test_cli_pipeline.py::test_optional_announcement_evidence_rejects_malformed_provider_payload tests/test_announcement_evidence.py::test_converts_supporting_cninfo_announcement_to_mapped_evidence -q`
  - Result: 2 passed.
- Related tests: `python -m pytest tests/test_announcement_evidence.py tests/test_cli_pipeline.py tests/test_cninfo_provider.py -q`
  - Result: 62 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 265 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed.
