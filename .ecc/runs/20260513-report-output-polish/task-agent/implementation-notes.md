# Implementation Notes

## Summary

Replaced Markdown-wrapped HTML output with a structured HTML renderer.

## Changes

- Added report writer test for semantic HTML.
- Rendered holdings as an HTML table.
- Rendered narratives as structured articles with dimension tables.
- Rendered evidence as lists.
- Preserved Markdown output unchanged.

## Result

Generated HTML reports now include real `<h1>`, `<section>`, and `<table>` elements and no longer display raw Markdown headings or table syntax.
