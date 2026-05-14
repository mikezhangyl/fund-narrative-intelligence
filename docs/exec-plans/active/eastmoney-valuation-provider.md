# Eastmoney Valuation Provider

## Goal

Replace the quote-derived valuation placeholder with a first real valuation
metrics provider path for Eastmoney A-share holdings.

## Scope

- Add an `EastmoneyValuationProvider` that fetches quote detail valuation fields
  such as PE, PB, market cap, and turnover-like context from Eastmoney.
- Extend `valuation-snapshot-v1` so it supports both `quote-derived-valuation`
  and `eastmoney-valuation`.
- Add `--valuation-source eastmoney` for explicit opt-in while preserving the
  existing quote-derived default.
- Wire reviewed-mapping enriched acceptance to the real valuation source.

## Non-Goals

- No Tushare/AKShare credentialed provider yet.
- No historical valuation percentile yet.
- No scoring weight changes.

## Acceptance

- Provider unit tests cover URL construction, normalization, and unavailable
  degradation.
- Pipeline tests cover explicit Eastmoney valuation snapshots in raw/scoring,
  provider foundation, source table, and reports.
- Reviewed-mapping enriched acceptance passes with `eastmoney-valuation`.
