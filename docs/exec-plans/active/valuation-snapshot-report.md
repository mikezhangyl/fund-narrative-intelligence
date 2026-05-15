# Valuation Snapshot Report

## Goal

Surface optional valuation snapshots in Markdown and HTML reports so users can
inspect valuation context behind valuation-derived signals.

## Scope

- Render a report section only when `valuation_snapshots` is present.
- Include stock, valuation basis, latest price, price change percent, PE TTM,
  PB, valuation pressure, provider, and source URL.
- Preserve source disclosure through existing provider-foundation notices.
- Keep scoring unchanged.

## Non-Goals

- No new valuation provider.
- No historical percentile valuation model.
- No frontend UI work.

## Acceptance

- Report tests fail first, then pass with Markdown and HTML valuation sections.
- Optional Eastmoney valuation pipeline test confirms generated reports include
  provider valuation metrics and source URL.
- Standard quality gates and acceptance scripts pass.
