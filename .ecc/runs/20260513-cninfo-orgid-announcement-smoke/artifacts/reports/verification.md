# Verification

## Commands

- `pytest tests/test_cninfo_provider.py -q`: passed, 7 tests.
- `pytest tests/test_announcement_smoke.py tests/test_main_cli.py::test_main_run_announcement_smoke_returns_status tests/test_main_cli.py::test_main_run_announcement_smoke_returns_nonzero_for_failed_summary tests/test_cninfo_provider.py -q`: passed, 13 tests.
- `python -m ruff check .`: passed.
- `python -m coverage run -m pytest -q`: passed, 76 tests.
- `python -m coverage report`: passed, total coverage 86%.
- `python -m compileall -q src tests scripts`: passed.
- `python -m src.main --run-announcement-smoke`: passed, 56 announcements and 56 evidence records for `161725`; notice check passed and effective quality was `partial`.
- `python -m src.main --run-real-smoke`: passed, six-fund Eastmoney smoke set.

## Notes

- The live announcement smoke writes `outputs/announcement_evidence_smoke_summary.json` and `outputs/announcement_evidence_smoke_summary.md`.
- Generated report data remains mixed-source because Eastmoney and CNINFO are real layers while registry, mappings, evidence, and signals are fixture-backed in V1.
