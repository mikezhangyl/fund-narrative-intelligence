# Reviewed Mapping Workspace Acceptance Verification

Status: passed

Commands:

- `python -m pytest tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: 2 passed
- `python -m ruff check scripts/validate_reviewed_mapping_enriched_acceptance.py tests/test_reviewed_mapping_enriched_acceptance_script.py`
  - Result: passed
- `python -m pytest tests/test_provider_derived_enriched_acceptance_script.py tests/test_reviewed_registry_enriched_acceptance_script.py tests/test_reviewed_mapping_enriched_acceptance_script.py tests/test_workspace_snapshot.py -q`
  - Result: 17 passed
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725`
  - Result: passed; built and validated `fund_161725_workspace_snapshot.json`
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed; generated raw, scoring, review queue, source table, manifest, markdown report, and HTML report artifacts
- `python -m coverage run -m pytest && python -m coverage report`
  - Result: 237 passed; total coverage 81%
