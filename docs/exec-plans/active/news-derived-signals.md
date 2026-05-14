# News Derived Signals

## Goal

Turn optional `news_evidence` into deterministic provider-derived momentum and
risk signals so news ingestion affects scoring without relying on fixture signal
events.

## Scope

- Add deterministic news-evidence signal derivation.
- Wire the derived events into raw/scoring `derived_signal_events` and
  `signal_events` when `--include-news-evidence` is enabled.
- Preserve the existing `Derived Signals` provider-foundation layer and disclose
  mixed derived sources when announcements, market quotes, and news are combined.
- Support `--base-intelligence-mode provider-derived` with CNINFO announcements
  plus news-derived evidence/signals.
- Add tests for positive, negative, and mixed news evidence conversion.

## Non-Goals

- No LLM classification.
- No article body parsing.
- No scoring model weight changes.
- No frontend UI.

## Acceptance

- `--include-news-evidence` adds news-derived signals when news evidence exists.
- Positive/mixed news can support `momentum_score`; negative news can add
  counter-evidence risk or momentum decay.
- Provider-derived mode can include news-derived signals without fixture signals.
- Full quality gates pass.
