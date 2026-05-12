---
name: api-contract-inference-from-ui
description: Use when browser network traces, HAR files, or UI-triggered API calls should be summarized into observed or inferred API contracts for black-box testing.
---

# API Contract Inference From UI

Use only from captured browser evidence. Do not claim backend implementation details.

## Status

- `observed`: request/response seen in trace or HAR
- `inferred`: behavior likely based on repeated UI outcomes
- `verified`: explicitly tested with repeatable checks

## Output

Update:

- `.ecc/test-runs/<run-id>/observations/api-observations.json`
- `docs/testing/system-card.md` Observed APIs
- `docs/testing/automation-candidates.md` when API-level smoke checks are valuable

