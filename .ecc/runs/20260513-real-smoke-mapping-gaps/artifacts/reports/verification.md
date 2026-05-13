# Verification

## Commands

- `pytest tests/test_real_fund_smoke.py -q`: passed, 4 tests.
- `python -m ruff check .`: passed.
- `python -m coverage run -m pytest -q`: passed, 76 tests.
- `python -m coverage report`: passed, total coverage 86%.
- `python -m compileall -q src tests scripts`: passed.
- `python -m src.main --run-real-smoke`: passed, six-fund Eastmoney smoke set.

## Live Mapping Gaps

- `320007`: `002594` 比亚迪, 汽车, 2.83%.
- `003834`: `600066` 宇通客车, 汽车, 3.83%.
- `001475`: `603308` 应流股份, 机械设备, 3.56%; `002246` 北化股份, 基础化工, 3.55%.
- `000991`: `002572` 索菲亚, 轻工制造, 4.03%; `603816` 顾家家居, 轻工制造, 3.92%; `002918` 蒙娜丽莎, 轻工制造, 3.76%.
