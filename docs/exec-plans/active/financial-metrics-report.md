# Financial Metrics Report

## Goal

Surface optional Eastmoney financial metrics in Markdown and HTML reports so
users can see the reported revenue/profit context behind financial-derived
signals.

## Scope

- Render a report section only when `financial_metrics` is present.
- Include stock, report date/type, revenue YoY, parent net profit YoY, provider,
  and source URL.
- Preserve mock/source disclosure through the existing provider-foundation
  notice.
- Keep the section presentation-only; no scoring changes.

## Non-Goals

- No new financial provider.
- No full financial statement parsing.
- No frontend UI work.

## Acceptance

- Report writer tests fail first, then pass with Markdown and HTML financial
  metric sections.
- Optional financial metrics pipeline test confirms generated reports include
  the metrics and provider source.
- Standard lint, compile, coverage, V1 acceptance, and enriched acceptance pass.
