# Task Brief

## Goal

Implement Linear MIK-48: define stable identity rules for candidates, evidence
packs, source events, mappings, review actions, and future promotion decisions.

## Scope

- Add a Narrative Service identity policy to the service contract.
- Add deterministic identity helpers for source events, intake candidates,
  stock+narrative evidence packs, candidate mappings, review actions, and future
  promotion decisions.
- Preserve duplicate/idempotency behavior in runtime code.
- Document stable ID rules in the Narrative Service runbook and startup memory.

## TDD Notes

- RED: contract test failed on missing `identity_policy`.
- RED: intake fallback test failed on missing `identity_metadata`.
- RED: review action idempotency test failed on missing `idempotency_key`.
- RED: evidence pack identity test failed on missing `evidence_pack_id`.
- GREEN: added identity helpers and integrated them into storage reads/writes.
