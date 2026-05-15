# Announcement Payload Validation

## Goal

Add explicit provider-contract validation for announcement metadata and
generated announcement evidence.

## Scope

- Validate announcement provider payload shape before conversion.
- Validate generated announcement evidence payload shape after conversion.
- Reject malformed provider payloads instead of silently producing empty
  evidence.

## Non-Goals

- No PDF parsing.
- No new announcement classification rules.
- No frontend UI.

## Acceptance

- Tests fail first for malformed announcement provider payloads.
- Announcement conversion outputs pass the new reusable validator.
- Standard quality gates pass, then the slice is merged and pushed.
