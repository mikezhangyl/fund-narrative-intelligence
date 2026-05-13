# Task Brief

## Goal

Implement the approved multi-match fallback policy: keep ambiguous fallback mappings, lower confidence, mark them for review, and expose precision flags in user-visible artifacts.

## Acceptance

- Multi-match fallback mapping confidence is reduced from `0.52` to `0.42`.
- Affected mappings include `needs_review` and `precision_flag`.
- Raw/scoring JSON include `mapping_precision_flags`.
- Markdown/HTML reports render Mapping Precision Flags.
- Full quality gates, real smoke, and announcement smoke pass before merge.
