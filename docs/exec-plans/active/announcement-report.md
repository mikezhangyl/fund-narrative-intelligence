# Announcement Report

## Goal

Surface optional CNINFO announcement metadata and generated announcement
evidence in Markdown and HTML reports.

## Scope

- Render `Announcements` when `announcements` is present.
- Render `Announcement Evidence` when `announcement_evidence` is present.
- Include stock, title, category, date, provider/source URL, narrative ID,
  confidence, evidence type, and generated summary.
- Preserve the limitation that V1 classifies announcement metadata and does not
  parse PDF contents.

## Non-Goals

- No PDF parsing.
- No new announcement provider.
- No frontend UI work.

## Acceptance

- Report tests fail first, then pass with announcement sections.
- Optional announcement pipeline test confirms generated reports include
  announcement metadata, generated evidence, source URL, and PDF limitation.
- Reviewed-mapping enriched acceptance requires announcement report sections.
