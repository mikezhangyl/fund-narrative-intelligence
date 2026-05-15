# V1 Data Layers Acceptance Verification

Status: passed

Commands:

- `python -m pytest tests/test_v1_acceptance_script.py::test_validate_acceptance_outputs_rejects_missing_data_layer_mock_source_url -q`
  - Result: red first, then passed after implementation
- `python -m pytest tests/test_v1_acceptance_script.py::test_validate_acceptance_outputs_rejects_missing_data_layer_mock_source_url tests/test_v1_acceptance_script.py::test_validate_v1_acceptance_script_passes_with_explicit_output_dir -q`
  - Result: passed, `2 passed in 0.05s`
- `python -m ruff check scripts/validate_v1_acceptance.py tests/test_v1_acceptance_script.py`
  - Result: passed
- `python -m ruff check .`
  - Result: passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed
- `python -m coverage run -m pytest -q && python -m coverage report`
  - Result: passed, `258 passed`, total coverage `80%`
