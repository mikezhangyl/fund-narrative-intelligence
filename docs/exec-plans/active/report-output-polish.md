# Report Output Polish Execution Plan

## Purpose

Make V1 HTML reports directly inspectable and suitable for user review.

## Scope

- Semantic HTML renderer.
- Tests for headings/tables/sections.
- Preserve existing Markdown report.

## Acceptance

- HTML report contains real `<h1>`, `<section>`, and `<table>` elements.
- HTML report does not display raw Markdown headings or table pipes.
- Existing CLI commands continue passing.

## Status

Implemented and locally verified.

## Run Record

- `.ecc/runs/20260513-report-output-polish/`
