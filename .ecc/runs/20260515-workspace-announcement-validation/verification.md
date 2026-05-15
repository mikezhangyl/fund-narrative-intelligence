# Verification

- RED: `python -m pytest tests/test_workspace_snapshot.py -q`
  - Result: failed as expected with two missing drift checks.
- GREEN target: `python -m pytest tests/test_workspace_snapshot.py -q`
  - Result: 16 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 261 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed and built/validated `fund_161725_workspace_snapshot.json`.
