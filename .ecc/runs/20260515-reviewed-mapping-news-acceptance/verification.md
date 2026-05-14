# Reviewed Mapping News Acceptance Verification

Status: passed

Commands:

- `python -m ruff check scripts/validate_reviewed_mapping_enriched_acceptance.py tests/test_reviewed_mapping_enriched_acceptance_script.py`
  - Result: passed
- `python -m pytest tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: 2 passed
- `python -m pytest tests/test_provider_derived_enriched_acceptance_script.py tests/test_reviewed_registry_enriched_acceptance_script.py tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: 6 passed
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed; generated raw, scoring, review queue, source table, manifest, markdown report, and HTML report artifacts
- `python -m coverage run -m pytest && python -m coverage report`
  - Result: 235 passed; total coverage 81%
