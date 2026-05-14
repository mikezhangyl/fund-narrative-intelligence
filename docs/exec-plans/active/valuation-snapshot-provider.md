# Valuation Snapshot Provider

## Goal

Add a lightweight valuation-context provider layer that can run end to end with
real market quote inputs, while keeping room to replace it with Tushare,
AKShare, or financial-report valuation data later.

## Scope

- Add a quote-derived valuation snapshot payload and provider layer.
- Expose it only when market quotes are included.
- Write valuation snapshots into raw/scoring artifacts and provider foundation.
- Keep the snapshot explicitly labeled as quote-derived context, not full
  fundamental valuation.

## Non-Goals

- Do not add Tushare/AKShare credentials or paid APIs.
- Do not change scoring weights in this slice.
- Do not build frontend UI.

## Acceptance

```bash
python -m src.main --fund-code 000001 --include-market-quotes --include-valuation-snapshots
```

Expected result:

- raw/scoring artifacts include `valuation_snapshots`.
- provider foundation includes a non-mock `valuation` layer when quote data is
  available.
- source table and workspace snapshot can expose the valuation layer.
