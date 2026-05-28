# Task Brief

## Linear

- Issue: MIK-44
- Title: [ARCH-P0] Trusted promotion transaction boundary
- Milestone: M3 - Trust Governance & Evidence

## Acceptance Focus

- Define the only legal transaction boundary for `candidate_untrusted -> trusted_validated`.
- Specify promotion command shape, atomic write set, rollback/failure behavior, and audit record schema.
- Prove intake, review action, and preflight cannot create trusted records or promotion decision records.

## TDD Plan

Add failing contract and HTTP invariants tests first, then implement the reserved promotion boundary metadata and ledger path without enabling promotion itself.
