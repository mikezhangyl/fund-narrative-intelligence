# Round 4 Operational Scheduling Run Ledger - 2026-05-30

Canonical readable artifact:
`docs/product/round4-operational-scheduling-run-ledger-2026-05-30.html`

Linear issues: `MIK-95`, `MIK-90`

Implemented service endpoints:

- `GET /api/v1/narratives/jobs/contract`
- `GET /api/v1/narratives/jobs/definitions`
- `POST /api/v1/narratives/jobs/run`
- `GET /api/v1/narratives/jobs/runs`

The service now models scheduled/manual operations through job definitions and
append-only `narrative-job-runs-v1` records. Manual runs support idempotency
keys, disabled jobs fail before writing a run, unsupported job types record a
failed run, and run records disclose `trusted_store_mutation=none`.
