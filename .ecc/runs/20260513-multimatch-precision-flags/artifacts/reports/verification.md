# Verification

## Commands

- `pytest tests/test_mapping_coverage.py tests/test_cli_pipeline.py::test_pipeline_surfaces_multi_match_precision_flags tests/test_report_writer.py -q`: passed, 7 tests.
- `python -m ruff check .`: passed.
- `python -m coverage run -m pytest -q`: passed, 79 tests.
- `python -m coverage report`: passed, total coverage 86%.
- `python -m compileall -q src tests scripts`: passed.
- `python -m src.main --run-real-smoke`: passed, six-fund Eastmoney smoke set with 100% coverage for every fund.
- `python -m src.main --run-announcement-smoke`: passed, 56 announcements and 56 evidence records for `161725`; notice check passed and effective quality was `partial`.

## Live Precision Flags

- `001475`: `300604` 长川科技 maps to Semiconductor Capex Cycle and Defense Aerospace, confidence lowered from `0.52` to `0.42`.
- `001475`: `600482` 中国动力 maps to New Energy Equipment and Defense Aerospace, confidence lowered from `0.52` to `0.42`.
