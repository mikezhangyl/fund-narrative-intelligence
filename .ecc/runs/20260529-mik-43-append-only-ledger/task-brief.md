# Task Brief

## Goal

Implement Linear MIK-43: define and enforce the durable append-only ledger
contract for Narrative Service review workflow storage.

## Scope

- Declare current JSON-ledger storage policy and future SQLite/Postgres migration
  boundary in `config/narrative_service_contract.yaml`.
- Ensure candidate intake and review-action runtime writes include append-only
  ledger metadata.
- Preserve non-promotion and non-mutation invariants for review actions,
  failed intake, and repeated reads.
- Document ledger behavior in the Narrative Service runbook and startup memory.

## TDD Notes

- RED: contract test failed on missing `storage_policy`.
- RED: review-action ledger test failed on missing `ledger_record_type`.
- RED: duplicate intake replay test failed on missing `ledger_sequence`.
- GREEN: added ledger schema metadata and policy documentation, then verified
  service and contract tests.
