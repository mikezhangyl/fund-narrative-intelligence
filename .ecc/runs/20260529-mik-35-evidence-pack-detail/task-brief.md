# Task Brief

## Goal

Implement Linear MIK-35: expose evidence pack detail and source drill-down for
stock-to-narrative mappings.

## Scope

- Add evidence pack detail lookup by `evidence_pack_id`.
- Add query-compatible lookup by `stock_code` + `narrative_id`.
- Return rationale, exclusions, confidence components, normalized evidence item
  source fields, supported claim types, and non-promotion metadata.
- Return structured missing envelopes without writing service data files.

## TDD Notes

- RED: evidence detail endpoint tests returned HTTP 404.
- RED: contract test failed because evidence pack detail was not declared.
- GREEN: added storage read model, HTTP routes, contract declaration, runbook,
  and startup memory updates.
