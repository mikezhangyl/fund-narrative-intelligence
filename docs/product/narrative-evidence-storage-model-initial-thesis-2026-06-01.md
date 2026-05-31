# Narrative Evidence Storage Model Initial Thesis - 2026-06-01

Linear issue: `MIK-243`

Follow-up architecture plan:
`docs/product/lightweight-narrative-lakehouse-architecture-2026-06-01.md`

## Plain-Language Answer

Yes, narrative service needs a database. But it should not put every file,
article, sentence, and narrative into one giant table.

The right model is layered storage:

1. Store source metadata and normalized facts in relational tables.
2. Store raw files or raw payloads as immutable blobs only when we have the
   right to store them.
3. Store sentence/paragraph evidence as small, traceable excerpts.
4. Store entity mentions and resolved entities separately.
5. Store search and embedding indexes as derived rebuildable indexes, not as the
   source of truth.

## Why This Matters

Narrative ingestion produces many different shapes:

- official announcement metadata
- PDF links or downloaded PDFs
- news headlines and article snippets
- full article text when licensed
- social posts
- individual sentences or paragraphs
- extracted entity mentions
- candidate narratives
- evidence packs
- human review decisions

These have different trust levels, licenses, retention rules, and query needs.
Treating all of them as "text" will make the system hard to audit and legally
dangerous. Treating all of them as "files" will make search, dedupe, and
evidence tracing weak.

## Recommended Storage Layers

### 1. Relational Core

Start with SQLite for local development and migrate to Postgres when the service
needs concurrent writes or production deployment.

Core tables:

- `source_registry`: one row per provider/source.
- `source_fetch_runs`: one row per fetch attempt or job.
- `source_documents`: one row per article, announcement, filing, PDF, post, or
  provider item.
- `source_events`: normalized events extracted from documents.
- `evidence_spans`: sentence/paragraph/title-level excerpts that support an
  event or narrative.
- `entity_mentions`: raw mentions found in documents/spans.
- `resolved_entities`: canonical stocks, funds, sectors, companies, policies,
  products, people, and concepts.
- `candidate_narratives`: grouped story candidates.
- `evidence_packs`: bundles of supporting and contradicting evidence.
- `review_ledger`: append-only human or system review decisions.
- `source_quality_snapshots`: health, reliability, freshness, and risk scores.

This is the source of truth for the product.

### 2. Blob / File Storage

Use filesystem locally, object storage later.

Store:

- raw provider JSON responses
- original announcement PDFs when legally allowed
- article HTML/text only when licensed or clearly permitted
- screenshots only for debugging, not default evidence

Do not store:

- full paywalled article text without a contract
- login-only/social content beyond permitted excerpts
- raw personal data that is not needed for narrative evidence

Blob paths should be content-addressed:

```text
blobs/{source_id}/{yyyy}/{mm}/{sha256}.{ext}
```

Relational rows should reference blob URI + content hash, not duplicate the blob.

### 3. Evidence Spans

Evidence spans are the small units the reviewer can actually inspect:

- headline
- article snippet
- announcement title
- PDF page excerpt when parsed later
- social post excerpt
- filing item excerpt

Each span should know:

- source document ID
- character offsets or extraction location when available
- excerpt text
- language
- source license scope
- extraction method
- confidence
- whether it supports, contradicts, or merely mentions a narrative

This layer is the bridge between raw source material and narrative reasoning.

### 4. Search Index

Search is a derived index, not the source of truth.

Start options:

- SQLite FTS5 for local MVP.
- Postgres `tsvector` when moving to Postgres.

Later options:

- OpenSearch/Elasticsearch if volume and query complexity justify it.

Search should index permitted text/excerpts, not restricted raw content.

### 5. Vector / Embedding Index

Vector search should be optional and derived.

Use cases:

- near-duplicate article clustering
- finding semantically similar evidence
- grouping emerging narrative candidates
- mapping new source events to existing narratives

Recommended starting point:

- no vector DB for V0 storage
- later use `pgvector` if Postgres is adopted

Embeddings should reference `evidence_span_id` or `source_document_id`. They
should not replace relational evidence records.

## Initial Table Shape

### `source_registry`

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

### `source_documents`

```text
document_id
source_id
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
trust_tier
parser_version
degradation_warnings
```

### `source_events`

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

```text
mention_id
document_id
evidence_span_id
raw_text
entity_type
resolved_entity_id
resolution_status
confidence
```

### `candidate_narratives`

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

```text
evidence_pack_id
candidate_narrative_id
supporting_span_ids
contradicting_span_ids
source_event_ids
quality_score
created_at
```

### `review_ledger`

```text
ledger_id
target_type
target_id
action
actor
reason
before_state
after_state
created_at
```

## Dedupe Keys

Use multiple levels:

- URL canonicalization for documents.
- Provider item ID when available.
- Raw content hash for exact duplicate detection.
- Normalized title hash for headline duplicates.
- Near-duplicate hash or embedding later for copied/syndicated articles.
- Stable entity IDs for cross-provider grouping.

## Retention And Copyright Rules

Default posture:

- Official disclosures: store metadata and links; store PDFs only if allowed and
  useful.
- Licensed news: store metadata, provider IDs, and permitted excerpts; store full
  text only if contract allows.
- Public news: store URL, title, snippet/excerpt, and fetched metadata; avoid
  unnecessary full-page archiving until permission is reviewed.
- Social/community: store minimal excerpt and aggregate heat metrics; avoid raw
  personal profile capture unless explicitly needed and permitted.

## Product Implication

The product should show a user:

- the narrative
- the evidence span
- the source document
- the source quality / license / trust label
- whether the evidence is primary fact, licensed news, context, or heat

This makes the system auditable. It also keeps future AI summarization grounded:
the model should summarize evidence packs, not invent narratives from anonymous
text blobs.

## Recommended Next Step

Architect should turn this thesis into a developer-ready schema plan under
`MIK-243`. Developer should not build large-scale source ingestion until this
storage contract is accepted.
