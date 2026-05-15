# Valuation Financial Boundary Tests

## Goal

Cover valuation and financial metrics provider-boundary validation with direct
regression tests.

## Scope

- Add malformed valuation provider payload test.
- Add malformed financial metrics provider payload test.
- Keep implementation unchanged unless tests expose a gap.

## Non-Goals

- No provider implementation changes.
- No report or scoring changes.

## Acceptance

- Tests prove valuation/financial injected providers cannot bypass contracts.
- Standard quality gates pass, then the slice is merged and pushed.
