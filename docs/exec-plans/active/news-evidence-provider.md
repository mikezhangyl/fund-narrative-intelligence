# News Evidence Provider

## Goal

Add an optional V1 news evidence provider layer that can collect RSS/search-style
headline evidence for mapped narratives without replacing the deterministic mock
baseline.

## Scope

- Add a no-key, injectable RSS-derived news evidence provider.
- Add CLI opt-in for single-fund runs.
- Emit `news_evidence` in raw/scoring JSON when enabled.
- Add a `News Evidence` provider-foundation/source-table layer.
- Surface user-visible disclosure that V1 classifies titles/snippets only and
  does not parse article bodies.
- Keep provider failures controlled with `unavailable` payloads and degradation
  events.

## Non-Goals

- No paid news/search API integration.
- No article body scraping or LLM sentiment analysis.
- No default-path network calls.
- No frontend UI.

## Acceptance

- `python -m src.main --fund-code 000001 --include-news-evidence`
  generates valid raw/scoring/report/source-table artifacts.
- `python -m src.main --validate-artifact-contracts <output-dir>` passes.
- Reports and source tables disclose the news provider, source URL, data quality,
  and title/snippet limitation.
- Full quality gates pass.
