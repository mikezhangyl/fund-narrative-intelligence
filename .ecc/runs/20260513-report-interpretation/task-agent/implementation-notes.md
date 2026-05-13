# Implementation Notes

## Summary

Added deterministic narrative interpretation fields and rendered them in reports.

## Changes

- Added `interpret_narrative`.
- Stored interpretation in scoring JSON for every mapped narrative.
- Rendered stage, risk, and confidence notes in Markdown and HTML.
- Added tests that guard against buy/sell/hold recommendation language in interpretation output.

## Result

Reports now explain what the lifecycle stage means, what risk pressure matters, and how confidence should be read without becoming investment advice.
