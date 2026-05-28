# Stock Narrative Service Runbook

Last updated: 2026-05-29

## Role

`stock-narrative-service` is an in-repo HTTP subservice under:

```text
services/stock-narrative-service/
```

It is a monorepo subservice, not an FNI internal module. FNI must consume it
through `NARRATIVE_SERVICE_URL`.

## Start

From the FNI repo root:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8800
```

Optional custom paths:

```bash
uv run python scripts/run_stock_narrative_service.py \
  --port 8800 \
  --registry-path data/registry/narrative_registry.reviewed.json \
  --mappings-path data/registry/stock_narrative_mappings.reviewed.json \
  --evidence-packs-path data/registry/mapping_evidence_packs.v0.json \
  --candidate-events-path data/fixtures/candidate_narrative_events.v1.json \
  --intake-ledger-path services/stock-narrative-service/data/runtime/candidate_intake_events.json \
  --review-actions-path services/stock-narrative-service/data/runtime/review_actions.json
```

## Health Check

```bash
curl http://127.0.0.1:8800/api/health
```

Expected:

```json
{
  "provider_version": "v0",
  "service": "stock-narrative-service",
  "status": "ok"
}
```

## Full Acceptance

The preferred local acceptance command starts the service on an ephemeral port,
runs FNI conformance, runs FNI provider smoke, and generates a deterministic
FNI fund holding exposure report with `narrative_source=narrative_service`.

```bash
uv run python scripts/validate_stock_narrative_service_acceptance.py
```

Expected summary:

```text
status=completed
conformance_status=completed
provider_smoke_status=completed
provider_smoke_source=narrative_service
report_status=completed
report_narrative_source=narrative_service
```

## Manual FNI Checks

When the service is already running:

```bash
NARRATIVE_SERVICE_URL=http://127.0.0.1:8800 \
uv run python scripts/run_narrative_service_conformance_probe.py

NARRATIVE_SERVICE_URL=http://127.0.0.1:8800 \
uv run python scripts/run_narrative_service_provider_smoke.py
```

## Endpoint Contract

Required endpoints:

```text
GET  /api/health
GET  /api/v1/narratives/registry
GET  /api/v1/narratives/mappings
POST /api/v1/narratives/intake/events
GET  /api/v1/narratives/candidates
GET  /api/v1/narratives/evidence-packs
GET  /api/v1/narratives/trust-audits/latest
GET  /api/v1/narratives/ops/summary
GET  /api/v1/narratives/review-queue
GET  /api/v1/narratives/review-actions
POST /api/v1/narratives/review-actions
POST /api/v1/narratives/promotion/preflight
```

`GET /api/v1/narratives/review-queue` supports optional `?status=` filtering.
Current queue statuses are `pending_review`, `ready_for_trust_audit`,
`approved_blocked_by_evidence`, `rejected`, and `deferred`. Queue rows include
latest review action, missing preflight gates, and recommended next action.

Every narrative endpoint must return:

```text
status
source
provider
provider_version
data
warnings
trust_metadata
```

Versioning is additive under `/api/v1/narratives`: new endpoints and optional
fields may be added without breaking existing conformance probes. Existing
required envelope fields must not be removed or renamed inside v1.

Error semantics:

- syntactically valid missing ids return a normalized envelope with
  `status=missing`, an error object in `data`, and a warning;
- invalid requests return HTTP 400 with `status=failed`, an error object in
  `data`, and a warning;
- degraded service state returns HTTP 200 with `status=degraded`, partial data
  where available, and warnings.

`GET /api/v1/narratives/ops/summary` returns service-level counts, current
trust statuses, review queue summary, and latest trust-audit result. It is an
operational snapshot, not a promotion or mutation endpoint.

## Trust Rules

The service must preserve current trust state:

- registry and stock mappings remain `untrusted_experimental`;
- evidence packs remain `candidate_untrusted`;
- intake-created rows remain candidates;
- intake must not create `trusted_validated` rows;
- review actions may record `approve`, `reject`, or `defer`, but they are
  ledger decisions only;
- review actions must not promote candidates into trusted registry or mapping
  records;
- promotion preflight may return `ready_for_trust_audit`, but it must not write
  trusted records or mutate registry/mapping stores.

## Ledger Storage

The current durable store is JSON-file-backed append-only ledgers:

- candidate intake writes `service-intake-events-v1` records to
  `candidate_intake_events.json`;
- review actions write `narrative-review-actions-v1` records to
  `review_actions.json`;
- trusted promotion decisions are reserved for a separate
  `narrative-promotion-decisions-v1` ledger and must not reuse the review-action
  file.

Each ledger record must preserve a schema version, record type, ledger sequence,
recorded timestamp, actor/action or event fields, note where applicable, source
metadata, and `promotion_effect=none` unless a future trusted-promotion endpoint
explicitly owns the write.

Reads replay seed fixture events first and intake ledger events second. Duplicate
candidate ids collapse to one candidate detail/read model, but duplicate intake
events remain in the append-only ledger for auditability. Repeated reads must not
write cache files or negative records. Failed intake validation must not create
ledger files.

SQLite or Postgres becomes the next store when concurrent reviewers, transactional
queries, or indexed ledger lookups are needed. That migration must not change the
HTTP contract: endpoint names, envelopes, trust states, append-only semantics,
and non-promotion invariants remain stable while only the storage adapter changes.

## Identity Rules

Explicit non-empty IDs from trusted inputs are preserved. When an input lacks an
ID, the service derives a deterministic hash ID from stable business fields:

- source events: `EVT_*` from source type, event time, source URL, title, and
  summary;
- candidate narratives: `C_INTAKE_*` from candidate name and canonical taxonomy;
- evidence packs: `EPACK_*` from stock code and narrative id;
- candidate mappings: `CMAP_*` from stock code and narrative id;
- future promotion decisions: `PD_*` from candidate id, target narrative id, and
  review action id.

Review actions use `RA_*`. Without an `idempotency_key`, every accepted action is
a new append-only ledger record. With an `idempotency_key`, the same candidate,
action, reviewer, and key returns the existing decision instead of appending a
duplicate record. Unknown candidate ids must fail before writing a review-action
ledger record.

## Troubleshooting

If conformance fails:

- check `/api/health`;
- confirm the service URL matches `NARRATIVE_SERVICE_URL`;
- confirm every narrative endpoint returns the normalized envelope;
- inspect `warnings` and `data.error` fields in the response.

If provider smoke falls back to `local_prototype`:

- the service was unreachable or returned invalid envelopes;
- check the provider smoke JSON warning code for `NARRATIVE_SERVICE_FALLBACK`;
- rerun conformance before debugging report code.

If a live FNI fund report fails while `narrative_source=narrative_service`:

- check fund profile and holdings provider failures first;
- this usually means market-data gateway/provider failure, not narrative service
  failure.

## Non-Goals

Do not add these to the first service lane:

- AI narrative discovery;
- social scraping;
- browser automation;
- production review UI;
- trusted automatic promotion;
- complex database architecture.
