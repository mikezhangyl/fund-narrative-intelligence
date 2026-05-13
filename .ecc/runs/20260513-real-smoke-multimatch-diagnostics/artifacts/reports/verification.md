# Verification

## Commands

- `pytest tests/test_real_fund_smoke.py -q`: passed, 4 tests.
- `python -m ruff check .`: passed.
- `python -m coverage run -m pytest -q`: passed, 77 tests.
- `python -m coverage report`: passed, total coverage 86%.
- `python -m compileall -q src tests scripts`: passed.
- `python -m src.main --run-real-smoke`: passed, six-fund Eastmoney smoke set with 100% coverage for every fund.

## Live Multi-Match Diagnostics

- `001475`: `300604` 长川科技 maps to Semiconductor Capex Cycle and Defense Aerospace.
- `001475`: `600482` 中国动力 maps to New Energy Equipment and Defense Aerospace.
