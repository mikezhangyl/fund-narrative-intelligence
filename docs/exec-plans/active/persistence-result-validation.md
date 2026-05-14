# Persistence Result Validation

## Goal

Add a reusable validator for review-action persistence result artifacts so
future web/API layers can verify audit records before loading or storing them.

## Acceptance

- Valid persistence result artifacts pass validation.
- Missing required fields fail with controlled contract errors.
- Malformed overwrite policy or registry delta fields fail with controlled
  contract errors.
- Persistence validates the result artifact before writing it.
