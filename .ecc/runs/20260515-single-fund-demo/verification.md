# Verification

- `python -m pytest tests/test_single_fund_demo.py -q` -> 3 passed
- `python scripts/run_single_fund_demo.py --output-dir outputs/demo_161725` -> passed
- `python scripts/validate_single_fund_demo.py --output-dir outputs/demo_161725` -> passed
- `python scripts/run_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded` -> passed; no mock layers, optional HK provider layers disclosed as unavailable
- `python scripts/validate_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded --expected-narrative "Hong Kong Tech Platforms"` -> passed
- Browser smoke at `http://127.0.0.1:8765/fund_161725_demo.html` -> rendered fund headline, stage, score, fallback notice, and holdings table
- Browser smoke at `http://127.0.0.1:8765/fund_513010_demo.html` -> rendered港股科技平台 narrative, radar chart, data-source unavailable disclosure, and no page-level horizontal overflow at 390px or 1280px viewport widths
- `python -m ruff check .` -> passed
- `python -m compileall -q src tests scripts` -> passed
- `python -m coverage run -m pytest -q && python -m coverage report` -> 280 passed, 81% total coverage
- `python scripts/validate_v1_acceptance.py` -> passed
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance` -> passed, `mock_layers=none`
