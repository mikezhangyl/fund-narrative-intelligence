# Task Brief

## Linear

- Issue: MIK-49
- Title: [ARCH-P1] Narrative trust state machine
- Milestone: M3 - Trust Governance & Evidence

## Acceptance Focus

- Document record states vs queue statuses in the narrative service contract.
- Assert forbidden transitions for intake, review action, and preflight.
- Provide stable report disclosure labels for candidate, reviewed-experimental, ready-for-audit, trusted, rejected, deferred, and local fixture states.

## TDD Plan

Add failing contract and report-renderer tests first, then implement the state-machine contract and disclosure helper.
