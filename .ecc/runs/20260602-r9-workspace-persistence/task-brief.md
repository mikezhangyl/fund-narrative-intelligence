# R9 Workspace Persistence

## Scope

Implement the FNI-owned persistent workspace store and saved-view contract:

- `MIK-177` Persistent workspace store and saved views.
- `MIK-180` Workspace persistence schema and repository contract.

## Acceptance

- Users/operators can save local views for product shell surfaces.
- Saved views persist across process restarts through a repository abstraction.
- Workspace state includes migration-ready backend metadata for JSON, SQLite, and Postgres.
- Product shell exposes workspace state as JSON and canonical Chinese HTML.
- Secrets and provider credentials are rejected from persisted workspace state.

## Verification

- TDD tests for repository persistence, immutability, secret rejection, CLI save-view behavior, route registry integration, and product shell outputs.
- Full project test suite, lint, diff whitespace, and ECC run validation.
