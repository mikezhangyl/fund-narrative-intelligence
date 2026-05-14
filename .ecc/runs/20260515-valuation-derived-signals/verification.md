# Valuation Derived Signals Verification

Status: passed

Commands:

- `python -m pytest tests/test_derived_signals.py -q` - passed, 11 tests.
- `python -m pytest tests/test_cli_pipeline.py::test_optional_valuation_snapshots_can_use_eastmoney_metrics tests/test_reviewed_mapping_enriched_acceptance_script.py -q` - passed, 4 tests.
- `python -m ruff check .` - passed.
- `python -m compileall -q src tests scripts` - passed.
- `python -m coverage run -m pytest -q && python -m coverage report` - passed, 245 tests, total coverage 81%.
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance` - passed.

Acceptance evidence:

- Reviewed-mapping enriched acceptance generated raw/scoring/report/source-table/manifest/workspace snapshot artifacts for fund `161725`.
- The live output included 8 `valuation_snapshot` derived signal events from `eastmoney-valuation`.
- `mock_layers=none` remained true for the reviewed-mapping enriched acceptance path.
