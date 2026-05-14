# Reviewed Mapping News Acceptance

## Goal

Keep the strict reviewed-mapping enriched acceptance path aligned with the
news-enabled provider-derived evidence and signal path.

## Scope

- Add `--include-news-evidence` to reviewed-mapping enriched acceptance.
- Require reviewed-mapping validation to pass through the reviewed-registry
  validator's news-enabled checks.
- Update mocked acceptance fixtures to include `news_evidence`, the
  `News Evidence` provider layer, and a news-derived signal.

## Non-Goals

- No new provider implementation.
- No scoring weight changes.
- No frontend UI.

## Acceptance

- Reviewed-mapping acceptance tests pass with news-enabled mocked outputs.
- Full quality gates pass before merge.
