# Task Brief

## Goal

Improve generated HTML reports so they render as structured reports instead of Markdown text wrapped in paragraphs.

## Scope

- Add tests for semantic HTML report structure.
- Render headings, holdings table, narrative cards, evidence lists, and disclaimer directly from structured scoring data.
- Preserve Markdown report output.

## Out Of Scope

- Frontend workspace.
- JavaScript interactivity.
- Charting.
- Report content/scoring model changes.

## Required Verification

- Full pytest suite.
- Acceptance command.
- Batch fixture command.
- HTML output inspection for semantic sections and no raw Markdown table syntax.
