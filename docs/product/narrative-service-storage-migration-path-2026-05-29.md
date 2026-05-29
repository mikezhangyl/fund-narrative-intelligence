# Narrative Service Storage Migration Path - 2026-05-29

## Scope

This slice records the Round 2 MIK-64 migration path from local JSON ledgers to a
SQLite-backed repository boundary, with Postgres deferred until the local
repository contract is proven.

HTTP contracts must remain storage-agnostic. The service should depend on the
repository method contract, not on file paths or SQL details.

## Current Store

Current storage remains JSON file ledgers:

- Candidate intake events
- Review actions
- Promotion decisions
- Reviewed registry fixture
- Reviewed stock mappings fixture
- Mapping evidence packs fixture

JSON ledger mode is acceptable while:

- A single local developer writes the ledgers.
- Review action volume is low.
- Query patterns are append/read-all.
- Recovery is possible from source-controlled fixtures plus runtime ledger
  backups.

## Migration Triggers

Move to SQLite when any of these become true:

- Multiple reviewers can write concurrently.
- Review queue filtering needs indexed queries.
- Promotion preflight requires transactional reads across candidate events,
  review actions, evidence links, and promotion decisions.
- Runtime ledgers exceed practical review size for full-file reads.
- Backup/replay needs point-in-time verification.

Move from SQLite to Postgres only after the SQLite repository boundary is proven
and production requires networked multi-user writes or managed backups.

## Repository Contract

The explicit repository methods are:

- `registry`
- `mappings`
- `evidence_packs`
- `candidates`
- `review_queue`
- `review_actions`
- `promotion_decisions`
- `ops_summary`

The current adapter is `JsonLedgerNarrativeRepository` with
`storage_backend=json_file_ledgers_v1`. A future SQLite adapter must satisfy the
same method contract.

## SQLite Schema Draft

Candidate source events:

- `source_event_id` primary key
- `source_type`
- `provider`
- `event_time`
- `title`
- `source_url`
- `dedupe_key`
- `payload_json`
- `created_at`

Candidate narratives:

- `candidate_narrative_id` primary key
- `name`
- `canonical_taxonomy`
- `trust_status`
- `human_review_status`
- `source_event_id`
- `payload_json`
- `created_at`

Review actions:

- `review_action_id` primary key
- `candidate_narrative_id`
- `action`
- `reviewed_by`
- `reviewed_at`
- `review_note`
- `idempotency_key`
- `payload_json`

Promotion decisions:

- `promotion_decision_id` primary key
- `candidate_narrative_id`
- `target_narrative_id`
- `review_action_id`
- `promotion_note`
- `created_at`
- `payload_json`

Evidence links:

- `evidence_link_id` primary key
- `source_event_id`
- `candidate_narrative_id`
- `stock_code`
- `narrative_id`
- `evidence_pack_id`
- `payload_json`

## Backfill And Replay

Backfill order:

1. Backup JSON ledgers.
2. Load source event ledger and preserve deterministic IDs.
3. Rebuild candidate narrative read model from source events.
4. Replay review actions by ledger sequence / reviewed_at.
5. Replay promotion decisions after review action references exist.
6. Recompute review queue and ops summary from SQLite.
7. Compare endpoint responses against JSON mode for registry, candidates,
   review queue, review actions, promotion decisions, and ops summary.

Replay must be idempotent. Existing deterministic IDs are the conflict keys.

## Backup And Recovery

Before migration:

- Copy JSON runtime ledgers to timestamped backup files.
- Store a manifest containing source path, target database path, row counts,
  checksum, and migration code version.

Recovery:

- JSON mode remains available as fallback until SQLite parity checks pass.
- SQLite database can be rebuilt from backed-up JSON ledgers.
- Failed migration must leave original JSON files untouched.

## Configuration

Local development:

- Default: `json_file_ledgers_v1`
- Optional future: `sqlite_local`
- Database path under ignored runtime data directory.

Production:

- Do not use Postgres until SQLite/local repository boundary has parity tests.
- Future Postgres adapter must implement the same repository contract and pass
  the same HTTP conformance suite.

## Verification

Current tests cover:

- JSON fixture repository behavior matches the existing `NarrativeStore`.
- The future repository method contract is explicit and can be satisfied by a
  SQLite-ready adapter.

No Postgres implementation is included in this slice.
