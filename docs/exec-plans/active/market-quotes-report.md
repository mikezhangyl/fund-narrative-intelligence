# Market Quotes Report

## Goal

Surface optional market quote snapshots in Markdown and HTML reports so users
can inspect price context behind market-quote-derived signals.

## Scope

- Render a report section only when `market_quotes` is present.
- Include stock, latest price, change percent, change amount, previous close,
  volume, provider, and source URL.
- Keep scoring unchanged.

## Non-Goals

- No new market data provider.
- No charting or frontend UI work.

## Acceptance

- Report tests fail first, then pass with Markdown and HTML market quote
  sections.
- Optional market quote pipeline test confirms generated reports include quote
  rows and source URL.
