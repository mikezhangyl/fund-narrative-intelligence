# Market Quotes Provider

## Goal

Add an optional real market quote layer for current fund holdings so generated
artifacts can carry a fresh price snapshot before quote data is used in scoring.

## Scope

- Add a market quote provider that attempts Eastmoney daily quote data and
  falls back to Yahoo chart data when Eastmoney is unavailable.
- Expose the provider through `--include-market-quotes`.
- Write `market_quotes` into raw and scoring artifacts.
- Add a `market_quotes` provider-foundation layer for future web source tables.
- Keep quote data out of V1 scoring for now.

## Acceptance

```bash
python -m src.main --fund-code 161725 --provider-mode eastmoney --include-market-quotes
```

Expected result:

- Raw and scoring JSON include `market_quotes`.
- The provider foundation includes a non-mock `Market Quotes` layer when live
  quotes are available.
- If one quote source is unavailable, fallback/degradation events are preserved
  rather than crashing report generation.
