# Task Brief

## Goal

Add real-smoke diagnostics for holdings that map to multiple narratives, so full mapping coverage does not hide precision risks.

## Acceptance

- Real smoke summary JSON includes `multi_mapped_holdings`.
- Real smoke Markdown includes a `Multi-Mapped Holdings` section when applicable.
- Per-fund failures and missing raw artifacts do not break smoke summary generation.
- Quality gates and live real smoke pass before merge.
