# Task Brief

## Linear

- Issue: MIK-36
- Title: [P0][PM] Market data capability inventory report
- Project: Fund Narrative Intelligence

## Goal

Build a simple capability inventory that tells the product owner what data FNI
can collect today, how it is sourced, whether it is stable enough for reports,
and which capability group it belongs to before requesting more gateway
expansion.

## Acceptance Focus

- JSON output is machine-readable and includes grouped inventory rows.
- HTML and Markdown readable summaries are available.
- Rows expose FNI consumer status, source provider, last-smoke status,
  degradation behavior, and Can-Do/unstable/blocked/future labels.
- Groups cover daily bars, fund holdings, sectors, flows, structure mapping,
  news, CYQ, and narrative service.
