# Workspace Data Layers Verification

Status: passed

Commands:

- `python -m pytest tests/test_workspace_snapshot.py::test_build_workspace_snapshot_from_output_directory tests/test_workspace_snapshot.py::test_workspace_snapshot_preserves_financial_metrics_layer_for_future_web tests/test_workspace_snapshot.py::test_workspace_snapshot_validation_rejects_data_layers_drift -q`
  - Result: passed, `3 passed in 0.05s`
- `python -m pytest tests/test_workspace_snapshot.py tests/test_v1_acceptance_script.py tests/test_main_cli.py -q`
  - Result: passed, `48 passed in 0.39s`
- `python scripts/validate_v1_acceptance.py`
  - Result: passed; built and validated `fund_000001_workspace_snapshot.json`
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance`
  - Result: passed; `financial_metrics=eastmoney`, `mock_layers=none`
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: passed, `257 passed`, total coverage `80%`
