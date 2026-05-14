# Review Action Delta

## Goal

Add a structured delta to review-action preview artifacts so future web approval
screens can show the candidate-state and active-narrative changes without
diffing the full registry payload.

## Acceptance

- Preview artifacts include `registry_delta`.
- `approve` lists added active narrative IDs and candidate field changes.
- `reject` / `defer` show no active narrative additions but still expose candidate state changes.
- Existing preview path safety remains intact.
