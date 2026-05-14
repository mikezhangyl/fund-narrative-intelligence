# V1 Workspace Snapshot Acceptance Verification

Status: passed

Commands:

- `python -m pytest tests/test_v1_acceptance_script.py -q`
  - Result: 3 passed
- `python -m ruff check scripts/validate_v1_acceptance.py tests/test_v1_acceptance_script.py`
  - Result: passed
- `python scripts/validate_v1_acceptance.py`
  - Result: passed; built and validated `fund_000001_workspace_snapshot.json`
- `python -m pytest tests/test_main_cli.py tests/test_contracts.py tests/test_workspace_snapshot.py tests/test_v1_acceptance_script.py -q`
  - Result: 55 passed
- `python -m compileall -q src tests scripts`
  - Result: passed
- `python -m ruff check .`
  - Result: passed
- `python -m coverage run -m pytest && python -m coverage report`
  - Result: 237 passed; total coverage 81%
