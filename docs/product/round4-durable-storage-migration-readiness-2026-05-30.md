# Round 4 Durable Storage Migration Readiness - 2026-05-30

Canonical readable artifact:
`docs/product/round4-durable-storage-migration-readiness-2026-05-30.html`

Linear issues: `MIK-96`, `MIK-91`

Implemented service endpoint:

- `GET /api/v1/narratives/storage/migration-plan`

The migration plan preserves `json_file_ledgers_v1` as the current mode while
declaring SQLite/Postgres target adapters, ten durable entities, append-only
idempotency rules, migration phases, parity check endpoints, and the invariant
that storage adapters must not change public HTTP contracts.
