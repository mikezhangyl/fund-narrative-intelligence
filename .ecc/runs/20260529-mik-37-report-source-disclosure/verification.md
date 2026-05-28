# Verification

TDD red:

- `uv run pytest tests/test_fund_holding_exposure_report.py::test_fund_holding_exposure_report_discloses_sources_and_degradation_in_html tests/test_fund_exposure_comparison_report.py::test_fund_exposure_comparison_report_discloses_market_data_source tests/test_fund_narrative_exposure_matrix_report.py::test_fund_narrative_exposure_matrix_report_discloses_market_data_degradation -q`
- Result before implementation: 3 failed because `market_data_source` was missing.

Green checks:

- Same targeted command -> 3 passed.
- `uv run pytest tests/test_fund_holding_exposure_report.py tests/test_fund_exposure_comparison_report.py tests/test_fund_narrative_exposure_matrix_report.py tests/test_stock_narrative_service_acceptance.py -q` -> 16 passed.
- `uv run python scripts/validate_stock_narrative_service_acceptance.py` -> completed; service-backed report completed.
- `uv run ruff check src/scanners/report_source_disclosure.py src/scanners/fund_holding_exposure_report.py src/scanners/fund_exposure_comparison_report.py src/scanners/fund_narrative_exposure_matrix_report.py tests/test_fund_holding_exposure_report.py tests/test_fund_exposure_comparison_report.py tests/test_fund_narrative_exposure_matrix_report.py` -> passed.
- `uv run python -m compileall -q src/scanners tests/test_fund_holding_exposure_report.py tests/test_fund_exposure_comparison_report.py tests/test_fund_narrative_exposure_matrix_report.py` -> passed.
- `git diff --check` -> passed.
