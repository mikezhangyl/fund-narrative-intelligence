# Market Quotes Acceptance

## Goal

Add a strict manual acceptance path for the optional market quote snapshot layer.

## Scope

- Run fund `161725` through `--provider-mode eastmoney`.
- Enable `--include-market-quotes`.
- Validate generated artifact contracts.
- Fail if holdings are not fresh Eastmoney data.
- Fail if market quote artifacts have no real quote rows.
- Keep registry, stock mapping, evidence, and signal fixtures explicit.

## Acceptance

```bash
python scripts/validate_market_quotes_acceptance.py --output-dir outputs/market_quotes_161725
```

Expected result:

- Holdings layer is fresh Eastmoney data.
- Market quote layer is non-mock and `fresh` or `partial`.
- Raw and scoring artifacts contain matching `market_quotes` payloads.
- Fixture-backed intelligence layers remain marked with `mock://fixtures/...`.
- Markdown and HTML reports disclose mixed real holdings/quotes and Mock fixture
  data.
