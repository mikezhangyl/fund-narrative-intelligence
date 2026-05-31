# Lightweight Narrative Lakehouse Architecture - 2026-06-01

Linear scope: `MIK-243`, `MIK-244`, `MIK-245`, `MIK-246`, `MIK-247`,
`MIK-248`, `MIK-249`

## Decision

Use a lightweight lakehouse architecture for Narrative Service source ingestion.

Boundary correction: the source-ingestion lakehouse belongs in
`stock-data-gateway`, not in FNI. This document now describes the target
gateway/source-platform architecture that FNI requests and consumes. FNI should
not implement upstream source adapters, raw blob storage, source fetch runs, or
canonical source-event persistence directly.

This means:

- not one giant database;
- not a heavyweight big-company data lake;
- a local-first version of lakehouse ideas that can grow later.

The MVP should combine:

1. a relational metadata/control-plane database;
2. a local raw file/object zone;
3. derived search indexes later;
4. derived vector indexes later, only when narrative retrieval needs them.

## Local Runtime Decision For Mac Development

Use two local runtime modes:

1. Fast test mode: SQLite plus temporary filesystem directories.
2. Integration mode: Docker Compose with Postgres plus an S3-compatible object
   store such as MinIO.

Do not require a bare host-installed database on the Mac. The Mac should run the
containers, but the database and raw object store should have explicit volumes,
ports, backup/reset commands, and environment variables.

This Docker runtime should be implemented by `stock-data-gateway`. FNI can run
consumer/integration tests against gateway endpoints, but should not own the
source storage runtime.

Why:

- it keeps the developer Mac clean;
- it makes the architecture closer to production without adding Kubernetes or
  cloud deployment work;
- it lets Developer run repeatable integration tests;
- it keeps database/object-store boundaries visible instead of hiding everything
  in random local folders;
- it gives a clear future migration path from local Docker to cloud Postgres and
  S3/MinIO/OSS.

Recommended local services:

```text
Postgres
  purpose: relational control plane for Silver/Gold tables
  local port: 5432 or project-specific override
  data: named Docker volume

MinIO
  purpose: Bronze raw object zone with S3-compatible API
  local ports: 9000 API, 9001 console
  data: named Docker volume or project-local bind mount
```

SQLite remains useful for unit tests and offline fixture mode, but the main
developer integration profile should prove the repository contract against
Postgres and raw object storage.

## Why This Is The Right Starting Point

The current problem is not petabyte-scale storage. The current problem is source
trust and traceability:

- Where did this narrative come from?
- Which source document supports it?
- Which exact sentence or paragraph supports it?
- Was the source official disclosure, licensed news, public context, or social
  heat?
- Do we have the right to store and display the original text?
- Can we replay the ingestion run?

A relational database is good at relationships and auditability. A raw object
zone is good at preserving original materials. Search/vector indexes are good at
retrieval, but they should be rebuildable from the source of truth.

## Mental Model

Use the classic lakehouse vocabulary, but implement it locally:

```text
Bronze = raw immutable source material
Silver = normalized source documents/events/evidence/entities
Gold   = narrative-ready evidence packs, digest rows, review state
```

Fast local test mode:

```text
data/narrative_lake/
  bronze/
    {source_id}/{yyyy}/{mm}/{dd}/{sha256}.{ext}
  manifests/
    blob_manifest.sqlite or manifest rows in the main DB

data/narrative_lakehouse.sqlite
  source_registry
  source_fetch_runs
  source_documents
  source_events
  evidence_spans
  entity_mentions
  resolved_entities
  candidate_narratives
  evidence_packs
  review_ledger
  source_quality_snapshots
```

Docker integration mode:

```text
docker compose up narrative-postgres narrative-minio

Postgres
  source_registry
  source_fetch_runs
  source_documents
  source_events
  evidence_spans
  entity_mentions
  resolved_entities
  candidate_narratives
  evidence_packs
  review_ledger
  source_quality_snapshots

MinIO bucket
  narrative-bronze/{source_id}/{yyyy}/{mm}/{dd}/{sha256}.{ext}
```

Future production:

```text
local filesystem / MinIO -> S3 / MinIO / OSS
SQLite / local Postgres  -> managed Postgres
SQLite FTS5      -> Postgres tsvector / OpenSearch
optional vectors -> pgvector / Milvus / dedicated vector service
```

## Storage Responsibilities

| Layer | Stores | Does not store | First implementation |
| --- | --- | --- | --- |
| Relational DB | IDs, relationships, metadata, normalized events, evidence spans, entity links, review decisions | large raw files or unauthorized full text | SQLite for tests, Docker Postgres for integration |
| Raw zone | raw JSON, PDFs, HTML, article text, files, when permitted | source-of-truth relationships | temp filesystem for tests, Docker MinIO/local object zone for integration |
| Search index | permitted titles/excerpts/text for keyword search | authoritative source records | later SQLite FTS5 |
| Vector index | embeddings for similar evidence/narrative retrieval | authoritative source records | deferred |

## Data Classes

### Raw Provider Payloads

Examples:

- SEC EDGAR JSON response.
- Tushare news response.
- Stocktwits symbol stream response.
- CNINFO announcement query response.

Default handling:

- Store raw JSON in bronze if source policy allows.
- Always store content hash and fetch metadata.
- Relational DB stores pointer to raw blob, not duplicated payload.

### Official Files

Examples:

- CNINFO PDF.
- SEC filing document.
- Exchange disclosure PDF.

Default handling:

- Store URL and metadata first.
- Download/store file only when allowed and useful.
- PDF text extraction is a later slice.

### News Articles

Examples:

- Google News RSS linked article.
- Sina Finance headline.
- Tushare news row.
- Licensed Reuters/Benzinga article.

Default handling:

- Store title, URL, source, published time, provider ID, and permitted excerpt.
- Store full text only if license permits.
- Keep `license_scope` and `retention_policy` explicit.

### Social / Community Posts

Examples:

- Stocktwits messages.
- Reddit posts/comments.
- Xueqiu/Guba/Weibo if access is approved later.

Default handling:

- Store minimal excerpt and aggregate heat metrics.
- Do not store unnecessary profile/personal data.
- Always mark as `heat_signal_only`.

### Evidence Spans

Evidence spans are first-class because they are what users inspect.

Examples:

- announcement title;
- article headline;
- article sentence;
- filing item excerpt;
- social post excerpt.

Each span should know:

- source document;
- source event;
- text excerpt;
- extraction method;
- license scope;
- stance: supports, contradicts, mentions;
- confidence;
- trust tier.

## MVP Relational Tables

### `source_registry`

Purpose: catalog source policy and source quality assumptions.

Fields:

```text
source_id
name
source_type
provider
trust_tier
permission_status
license_scope
retention_policy
redistribution_policy
anti_bot_risk
owner_service
enabled
created_at
updated_at
```

### `source_fetch_runs`

Purpose: make ingestion replayable and auditable.

Fields:

```text
fetch_run_id
source_id
started_at
finished_at
status
request_params_json
row_count
skipped_count
degraded_count
failure_reason
latency_ms
created_at
```

### `source_documents`

Purpose: one canonical row per article, filing, PDF, announcement, post, or
provider item.

Fields:

```text
document_id
source_id
fetch_run_id
provider_item_id
canonical_url
title
published_at
fetched_at
language
document_type
raw_hash
blob_uri
license_scope
retention_policy
trust_tier
parser_version
degradation_warnings_json
created_at
```

### `source_events`

Purpose: normalized facts or signals extracted from documents.

Fields:

```text
source_event_id
document_id
event_type
event_time
summary
source_trust_tier
confidence
freshness_bucket
extraction_method
created_at
```

### `evidence_spans`

Purpose: inspectable proof units.

Fields:

```text
evidence_span_id
document_id
source_event_id
span_type
text_excerpt
char_start
char_end
page_number
stance
license_scope
extraction_method
confidence
created_at
```

### `entity_mentions`

Purpose: preserve raw mentions before resolution.

Fields:

```text
mention_id
document_id
evidence_span_id
raw_text
entity_type
resolved_entity_id
resolution_status
confidence
created_at
```

### `resolved_entities`

Purpose: canonical entities.

Fields:

```text
resolved_entity_id
entity_type
canonical_name
primary_symbol
market
aliases_json
external_ids_json
created_at
updated_at
```

### `candidate_narratives`

Purpose: grouped story candidates.

Fields:

```text
candidate_narrative_id
title
summary
status
first_seen_at
last_seen_at
trend_state
trust_state
created_at
updated_at
```

### `evidence_packs`

Purpose: link narratives to supporting and contradicting evidence.

Fields:

```text
evidence_pack_id
candidate_narrative_id
supporting_span_ids_json
contradicting_span_ids_json
source_event_ids_json
quality_score
created_at
```

### `review_ledger`

Purpose: append-only review and promotion decisions.

Fields:

```text
ledger_id
target_type
target_id
action
actor
reason
before_state_json
after_state_json
created_at
```

## Blob / Raw Zone Layout

Use content-addressed paths:

```text
data/narrative_lake/bronze/{source_id}/{yyyy}/{mm}/{dd}/{sha256}.{ext}
```

Examples:

```text
data/narrative_lake/bronze/sec_edgar/2026/06/01/abc123.json
data/narrative_lake/bronze/cninfo/2026/06/01/def456.pdf
data/narrative_lake/bronze/stocktwits/2026/06/01/ghi789.json
```

Blob manifest fields:

```text
blob_uri
source_id
fetch_run_id
document_id
sha256
mime_type
size_bytes
retention_policy
license_scope
created_at
```

Rule: if retention policy says metadata-only, save DB metadata and skip raw
blob persistence.

## Dedupe Strategy

Use layered dedupe:

- provider item ID when available;
- canonical URL;
- raw content SHA-256;
- normalized title hash;
- later near-duplicate text hash;
- later embedding similarity for narrative clustering.

Dedupe must not erase lineage. If two providers carry the same article, keep
provider/source provenance while collapsing duplicate document content.

## Search And Vector Position

V0 should not start with a vector database.

Start without dedicated search if the volume is small. Add SQLite FTS5 only when
review/search workflows need it.

Upgrade path:

```text
No search index
  -> SQLite FTS5 over permitted titles/excerpts
  -> Postgres tsvector
  -> OpenSearch if query complexity/scale requires it
```

Vector path:

```text
No embeddings
  -> local/offline embeddings for evidence spans
  -> pgvector when Postgres is adopted
  -> dedicated vector service only if needed
```

Search/vector indexes are always derived and rebuildable from relational tables
and permitted raw/excerpt storage.

## Gateway Build Order

1. `MIK-245`: accept the architecture spec.
2. Gateway change request:
   `/Users/mikezhang/Coding/AI-Learning/stock-data-gateway/docs/product/fni-narrative-source-lakehouse-capability-change-request-2026-06-01.md`
3. Gateway adds Docker local lakehouse runtime profile.
4. Gateway implements repository contract and core source tables.
5. Gateway implements local raw zone and blob manifest.
6. Gateway connects first source capabilities:
   - SEC EDGAR;
   - CNINFO official disclosures;
   - public news context;
   - Stocktwits heat pilot.
7. FNI updates consumer contracts, client wrappers, conformance probes, and
   report/UI source quality rendering after gateway routes exist.
8. `MIK-248`: add search/vector deferral plan; do not implement vector DB yet.

## Interview-Ready Explanation

The system starts with a lightweight lakehouse:

- Bronze stores immutable raw source material in a local object-style layout.
- Silver stores normalized source events, evidence spans, and entity resolution
  in a relational database.
- Gold stores narrative candidates, evidence packs, review decisions, and digest
  outputs.
- Search and vector indexes are derived indexes that can be rebuilt.

This avoids premature big-data infrastructure while preserving the core
lakehouse principle: raw data, normalized data, and product-ready data are
separate layers with lineage between them.

## Non-Goals

- No Hadoop/Spark/S3-first architecture now.
- No bare host-installed database requirement on the Mac.
- No production Postgres or cloud object storage requirement for the first local
  slice.
- No vector DB in V0.
- No full-text retention for paid/news/social sources unless permitted.
- No source adapters bypassing source registry and retention policy.
