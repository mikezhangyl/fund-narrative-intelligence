# Round 4 Productized Narrative Operations Plan - 2026-05-30

## Capability

Round 4 moves the system from completed Can-Do capability slices into a productized operating loop. Operators should be able to validate live data access, view Narrative Radar as a service product surface, schedule intake/scoring/report operations, migrate toward durable storage, and complete review/trust workflows with auditability.

## Product Direction

The next product state should be:

- live data/provider readiness can be checked before running downstream workflows
- Narrative Radar is visible as an operator-facing service UI, not only an API payload
- source intake and radar scoring can be run manually or scheduled
- narrative lifecycle state can migrate from JSON/fixture-ready stores to durable SQLite/Postgres
- reviewers can complete the candidate -> evidence -> review -> preflight -> promotion path

This is still not strategy development, AI prediction, trading execution, or social-media scraping.

## PM Requirements

### MIK-86 - PM Parent

`[PM-R4] Product requirement pack for productized narrative operations`

Round 4 turns completed developer capabilities into a repeatable product loop. It covers live credential smoke, Narrative Radar UI, scheduling, durable database migration readiness, and complete review/trust workflows.

### MIK-88 - Live Provider Credential Smoke Dashboard

Users need one place to confirm whether real Tushare, gateway, and Narrative Service credentials/configuration work before trusting downstream radar or report output.

Acceptance focus:

- classify configured/reachable/permissioned/degraded/blocked states
- keep partial provider failures from failing the whole check
- never expose secrets
- link failures to owning service or next action

### MIK-89 - Narrative Radar UI As Service Product Surface

Narrative Radar should become a service-owned operator surface. It should render dominant, emerging, heating, stable, and cooling narratives as a bubble map backed by Narrative Service data.

Acceptance focus:

- bubble size reflects heat
- bubble color reflects momentum
- bubble position reflects trend and market confirmation
- trust/evidence quality is visible
- UI consumes Narrative Service radar data without recomputing scores

### MIK-90 - Operational Scheduling For Source Intake And Radar Scoring

Operators should be able to configure scheduled jobs and see whether source intake, radar scoring, live smoke, or report-pack generation succeeded, degraded, or failed.

Acceptance focus:

- schedules can be enabled/disabled
- each run has id, timestamps, status, duration, warnings, and artifact links
- failed jobs do not corrupt trusted stores
- manual run remains available for local validation

### MIK-91 - Persistent Database Migration Readiness

The service should be ready to move beyond JSON/fixture-style persistence into SQLite or PostgreSQL without changing public HTTP contracts.

Acceptance focus:

- tables/entities are planned for narratives, mappings, evidence, source events, candidates, review actions, promotion decisions, radar snapshots, and job runs
- idempotency and append-only semantics are preserved
- existing local mode remains available until migration is proven

### MIK-92 - Complete Review Workflow For Evidence Drill-Down And Trust Promotion

Reviewers need a complete workflow from candidate narrative discovery to evidence review and trust promotion, with safeguards against promoting weak or unverified mappings.

Acceptance focus:

- review queue by status
- candidate and evidence drill-down
- review action submission
- promotion preflight
- all-or-none promotion commit
- clear blocked reasons and audit trail

## Architect Requirements

### MIK-87 - Architect Parent

`[ARCH-R4] Architecture requirement pack for productized narrative operations`

Define the architecture needed to move from Can-Do scripts/contracts to a repeatable product loop: live credential validation, UI-serving contracts, scheduling boundaries, durable storage migration, and workflow state/audit integrity.

### MIK-93 - Live Validation Taxonomy And Credential-Safe Diagnostics

Define provider validation states and safe diagnostics.

Required classifications:

- `configured`
- `not_configured`
- `reachable`
- `provider_permission_required`
- `request_timeout`
- `upstream_degraded`
- `schema_mismatch`
- `contract_failed`
- `success`

### MIK-94 - Narrative Radar UI Contract And Frontend Boundary

Define how the Narrative Service UI consumes radar data without moving score logic into client code or FNI reports.

Boundary:

- Narrative Service API owns score fields and components
- UI owns rendering, filters, interactions, and drill-down navigation
- FNI may link to radar later but must not calculate radar data

### MIK-95 - Scheduling Job Model And Run Ledger

Define job/run records for scheduled and manual operations.

Required concepts:

- job definition: id, type, enabled, schedule, parameters, owner service
- run ledger: run id, job id, timestamps, status, duration, warnings, artifacts, error category
- bounded execution: timeout, concurrency guard, retry policy, idempotency key

### MIK-96 - Durable Store Migration Schema For Narrative Lifecycle

Define a durable store migration schema that preserves HTTP contracts and append-only semantics.

Required entities:

- narratives
- stock narrative mappings
- evidence packs
- source events
- candidate narratives
- review actions
- promotion decisions
- radar source signals
- radar snapshots
- job runs

### MIK-97 - Review And Promotion Workflow State Machine

Define the candidate/review/preflight/promotion state machine.

Required rules:

- intake creates candidates only
- review actions can approve/reject/defer but cannot promote directly
- preflight is non-mutating
- promotion commit is the only trusted-record write path
- failed promotion writes no trusted records

## Dependency Plan

- MIK-88 is blocked by MIK-93.
- MIK-89 is blocked by MIK-94.
- MIK-90 is blocked by MIK-93 and MIK-95.
- MIK-91 is blocked by MIK-96.
- MIK-92 is blocked by MIK-97.

## Recommended Developer Order

1. MIK-93: implement the live validation taxonomy and secret-safe diagnostics contract.
2. MIK-88: build live provider credential smoke output/surface.
3. MIK-94: lock the Narrative Radar UI contract and frontend boundary.
4. MIK-89: build the Narrative Radar service UI.
5. MIK-97: formalize review/promotion state machine.
6. MIK-92: implement the complete review workflow surface.
7. MIK-95 + MIK-90: add scheduling and run ledger after the manual flows are stable.
8. MIK-96 + MIK-91: prepare durable storage migration after workflow entities are stable.

## Non-Goals

- no AI prediction
- no trading execution
- no fund recommendation engine
- no social scraping
- no browser automation
- no anti-bot/proxy infrastructure
- no direct provider access inside FNI when gateway/service contracts exist

## Acceptance Gate

Round 4 is accepted when a developer can demonstrate a bounded product loop:

1. run live provider credential smoke
2. view Narrative Radar through service-owned UI or validated UI contract
3. inspect a candidate narrative through evidence drill-down
4. complete review/preflight/promotion on deterministic fixture data
5. show scheduling and durable-store migration paths are explicitly modeled, even if not fully production-hardened
