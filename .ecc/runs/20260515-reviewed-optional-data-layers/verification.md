# Verification

- RED: `python -m pytest tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: failed as expected with missing `announcement_evidence` and `market_quotes` data-layer checks.
- GREEN target: `python -m pytest tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: 6 passed.
- RED bug regression: `python -m pytest tests/test_workspace_snapshot.py::test_workspace_snapshot_counts_announcement_evidence_for_future_web -q`
  - Result: failed as expected because `announcement_evidence` item_count was 0.
- GREEN target: `python -m pytest tests/test_workspace_snapshot.py tests/test_reviewed_mapping_enriched_acceptance_script.py -q`
  - Result: 23 passed.
- Quality: `python -m ruff check .`
  - Result: passed.
- Quality: `python -m compileall -q src tests scripts`
  - Result: passed.
- Acceptance: `python scripts/validate_v1_acceptance.py`
  - Result: passed.
- Full tests: `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: 264 passed, total coverage 80%.
- Enriched acceptance: `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed.
