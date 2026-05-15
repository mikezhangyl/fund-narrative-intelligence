# News Evidence Report

## Goal

Surface optional RSS-derived news evidence in Markdown and HTML reports so users
can inspect title/snippet evidence and query coverage behind news-derived
signals.

## Scope

- Render a report section only when `news_evidence` is present.
- Include query coverage, title, narrative ID, sentiment, confidence, event
  date, provider, source URL, and classification reason.
- Preserve the existing limitation that V1 classifies RSS titles/snippets only.

## Non-Goals

- No article body parsing.
- No new news provider.
- No frontend UI work.

## Acceptance

- Report tests fail first, then pass with Markdown and HTML news evidence
  sections.
- Optional news evidence pipeline test confirms generated reports include news
  rows and source URL.
- Reviewed-mapping enriched acceptance requires `News Evidence` in reports.
