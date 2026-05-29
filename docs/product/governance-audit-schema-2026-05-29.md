# Governance Audit Schema - 2026-05-29

## Scope

This slice implements the Round 2 MIK-66 architecture contract for governance
audit exports. The machine-readable schema is
`config/governance_audit_schema.json`.

## Record Types

The schema supports:

- `narrative`
- `candidate_narrative`
- `stock_mapping`
- `candidate_mapping`
- `evidence_pack`
- `promotion_decision`

## Trust-State Fields

Every export row is expected to carry:

- `status`
- `trust_status`
- `human_review_status`
- `source_store`
- `service_ledger_approval_id`

The export is read-only and must not mutate narrative, mapping, evidence, or
promotion stores.

## Warning Policy

Promoted-looking records with `trusted_validated` trust state and approved human
review but without service-ledger approval are flagged as
`missing_service_ledger_approval`.

This warning is PM-facing as:

`Promoted-looking record lacks service-ledger approval.`

The same code is also developer-facing for migration and ledger reconciliation.

## CSV-Friendly Flattening

The schema records list flattening with ` | ` as the list separator so JSON rows
can be exported to CSV without losing warning code readability.

## Output

The export builder emits JSON and Chinese HTML table-compatible payloads using
`governance-audit-export-v1`. The schema is designed for reuse by the future
durable storage migration and service-ledger reconciliation work.
