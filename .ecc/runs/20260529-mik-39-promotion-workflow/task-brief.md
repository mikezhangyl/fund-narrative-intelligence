# Task Brief

## Linear

- Issue: MIK-39
- Title: [P0][PM] Trusted promotion workflow with explicit gates
- Milestone: M3 - Trust Governance & Evidence

## Acceptance Focus

- Promotion requires source evidence, rationale, exclusion criteria, human approval, and trust audit pass.
- Promotion produces a separate auditable `PD_*` decision record.
- Raw intake, review action alone, and preflight alone cannot promote.
- Failed promotion gates explain exactly what is missing.
- Promoted records become distinguishable as `trusted_validated`.

## TDD Plan

Add failing HTTP tests for failed gates and successful atomic promotion first, then implement the commit endpoint and ledger/store writes.
