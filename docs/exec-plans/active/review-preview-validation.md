# Review Preview Validation

## Goal

Add a reusable validator for review-action preview artifacts so future web/API
layers can fail fast on malformed preview payloads.

## Acceptance

- Valid preview artifacts pass validation.
- Missing required top-level fields fail with controlled contract errors.
- Malformed `registry_delta` payloads fail with controlled contract errors.
- Preview writer validates artifacts before writing them.
