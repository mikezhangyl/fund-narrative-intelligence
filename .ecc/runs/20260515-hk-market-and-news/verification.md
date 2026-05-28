# Verification

- `python -m pytest tests/test_eastmoney_market_provider.py tests/test_eastmoney_valuation_provider.py tests/test_eastmoney_financial_metrics_provider.py tests/test_news_provider.py -q` -> 19 passed
- `python -m pytest tests/test_single_fund_demo.py tests/test_eastmoney_market_provider.py tests/test_eastmoney_valuation_provider.py tests/test_eastmoney_financial_metrics_provider.py tests/test_news_provider.py -q` -> 27 passed
- `python -m ruff check src/providers/security_market.py src/providers/eastmoney_market.py src/providers/eastmoney_valuation.py src/providers/eastmoney_financials.py src/providers/news.py src/orchestrator.py tests/test_single_fund_demo.py tests/test_eastmoney_market_provider.py tests/test_eastmoney_valuation_provider.py tests/test_eastmoney_financial_metrics_provider.py tests/test_news_provider.py` -> passed
- `python -m compileall -q src tests scripts` -> passed
- `python scripts/run_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded` -> passed
- `python scripts/validate_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded --expected-narrative "Hong Kong Tech Platforms"` -> passed
- `python scripts/run_single_fund_demo.py --output-dir outputs/demo_161725` -> passed
- `python scripts/validate_single_fund_demo.py --output-dir outputs/demo_161725 --expected-narrative "Premium Baijiu Consumption"` -> passed
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance` -> passed
