# Validate Signal Trace CLI Verification

Status: passed

Commands:

- `python -m pytest tests/test_main_cli.py::test_main_validates_signal_trace_artifact tests/test_main_cli.py::test_main_validate_signal_trace_rejects_malformed_file -q` - passed, 2 tests.
- `python -m pytest tests/test_main_cli.py tests/test_v1_acceptance_script.py -q` - passed, 34 tests.
- `python scripts/validate_v1_acceptance.py` - passed.
- `python -m ruff check src/main.py tests/test_main_cli.py docs/product/README.md docs/product/v1-implementation-spec.md docs/memory/project-context.md docs/memory/architecture-decisions.md` - passed.
- `python -m coverage run -m pytest -q && python -m coverage report` - passed, 249 tests, total coverage 80%.
