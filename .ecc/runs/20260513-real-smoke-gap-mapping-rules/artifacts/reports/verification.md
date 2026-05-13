# Verification

## Commands

- `pytest tests/test_mapping_coverage.py -q`: passed, 4 tests.
- `python -m ruff check .`: passed.
- `python -m coverage run -m pytest -q`: passed, 77 tests.
- `python -m coverage report`: passed, total coverage 86%.
- `python -m compileall -q src tests scripts`: passed.
- `python -m src.main --run-real-smoke`: passed, six-fund Eastmoney smoke set with 100% coverage for every fund.
- `python -m src.main --run-announcement-smoke`: passed, 56 announcements and 56 evidence records for `161725`; notice check passed and effective quality was `partial`.

## Notes

- Registry broadening only added terms; the fallback mapping algorithm was unchanged.
- Stage distribution stayed stable: `strengthening`, `diverging`, and `weakening`.
