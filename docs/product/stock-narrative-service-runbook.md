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
  --review-actions-path services/stock-narrative-service/data/runtime/review_actions.json \
  --promotion-decisions-path services/stock-narrative-service/data/runtime/promotion_decisions.json
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
GET  /api/v1/narratives/candidates/{candidate_narrative_id}
GET  /api/v1/narratives/evidence-packs
GET  /api/v1/narratives/evidence-packs/{evidence_pack_id}
GET  /api/v1/narratives/evidence-packs/detail?stock_code=...&narrative_id=...
GET  /api/v1/narratives/trust-audits/latest
GET  /api/v1/narratives/ops/summary
GET  /api/v1/narratives/review-queue
GET  /api/v1/narratives/review-actions
POST /api/v1/narratives/review-actions
POST /api/v1/narratives/promotion/preflight
POST /api/v1/narratives/promotion/commit
```

`GET /api/v1/narratives/review-queue` supports optional `?status=` filtering.
Current queue statuses are `pending_review`, `ready_for_trust_audit`,
`approved_blocked_by_evidence`, `rejected`, and `deferred`. Queue rows include
latest review action, missing preflight gates, and recommended next action.

`GET /api/v1/narratives/candidates/{candidate_narrative_id}` returns one
candidate read model with candidate metadata, trust status, full review history,
latest review action, promotion preflight gates, missing gates, recommended next
action, and source evidence references. Unknown candidate ids return a
`status=missing` envelope with `CANDIDATE_NOT_FOUND`; they must not write review,
intake, registry, mapping, or evidence files.

Evidence pack detail can be loaded by `evidence_pack_id` or by stock+narrative
query fields. The response includes mapping rationale, exclusion rationale,
confidence components, normalized evidence items, and `promotion_effect=none`.
Missing packs return a `status=missing` envelope with `EVIDENCE_PACK_NOT_FOUND`
and must not write review, intake, registry, mapping, or evidence files.

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

Most narrative envelopes also include optional `diagnostics` using
`narrative-operational-diagnostics-v1`. The diagnostics object is intentionally
lightweight and does not require tracing, metrics backends, proxies, browser
automation, or anti-detect infrastructure. It separates:

- `product_data_gaps`: business data is incomplete while the service/runtime is
  healthy;
- `system_failures`: a service/runtime/provider operation failed or returned
  invalid data;
- `status_summary`: status, warning count, product data gap count, and system
  failure count;
- `provider_source`: source, provider, provider version, fetch mode, and
  fallback source.

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
operational snapshot, not a promotion or mutation endpoint. The endpoint's
`data.diagnostics` is the canonical service operational snapshot for developer
handoffs and CI-style acceptance checks.

## Provider-Aware Intake

`POST /api/v1/narratives/intake/events` accepts structured event sources with
these source types:

- `news`
- `announcement`
- `manual`
- `social_future`

For `news` and `announcement`, gateway-owned or Tushare-backed structured feeds
are preferred before any public website crawling. Public news or announcement
website crawling is fallback-only after permission review. Every accepted intake
record normalizes provider/source metadata, including `provider`,
`provider_version`, `permission_status`, and `degradation_state`.

Intake can return two review-only outputs:

- `candidate_narratives`, always with `trust_status=candidate_untrusted`;
- `evidence_reinforcements`, for events that reinforce existing narrative ids,
  always with `trust_status=candidate_untrusted` and `promotion_effect=none`.

Neither output promotes registry narratives, stock mappings, evidence packs, or
trusted stores. Existing narrative reinforcement is source evidence for human
review and later gates only.

## Trust State Machine

Record states:

- `local_fixture`: local fixture or fallback data only.
- `candidate_untrusted`: review input created by intake, evidence packs, or
  other candidate surfaces.
- `reviewed_experimental`: limited human-reviewed or seeded data that is useful
  for observation/audit but is not trusted production knowledge. Existing
  `untrusted_experimental` and `reviewed_untrusted` values are disclosure
  aliases for this state.
- `trusted_validated`: data promoted only through a future atomic promotion
  transaction after evidence, rationale, exclusion criteria, human approval,
  trust-audit pass, and auditable decision record.

Queue statuses are separate from record states: `pending_review`,
`approved_blocked_by_evidence`, `ready_for_trust_audit`, `rejected`, and
`deferred`.

Forbidden transitions:

- intake must not create `reviewed_experimental` or `trusted_validated`;
- review actions must not mutate record state;
- promotion preflight is read-only and must not create trusted records;
- trust audit can produce an audit result, but only the future promotion
  transaction may write `trusted_validated`.

## Promotion Transaction Boundary

The reserved promotion command surface is:

```text
POST /api/v1/narratives/promotion/commit
```

It is the only legal write boundary for `candidate_untrusted ->
trusted_validated` and requires:

- candidate id and target narrative id;
- review action id with latest action `approve`;
- trust audit id with result `passed`;
- promoter identity and promotion note;
- source evidence, mapping rationale, and exclusion criteria gates already
  satisfied.

The transaction write set is all-or-none:

- trusted registry record;
- trusted stock mapping record;
- trusted evidence pack record;
- promotion decision ledger record.

Partial writes are forbidden. Failed promotion commands must write no records.
Retry semantics must be idempotent only after a successful decision exists.
Promotion decisions use the append-only `narrative-promotion-decisions-v1` ledger
and `PD_*` immutable decision ids.

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

## Review Workspace

Generate a local reviewer workspace from a running service:

```bash
uv run python scripts/run_narrative_review_workspace.py \
  --service-url http://127.0.0.1:8800 \
  --output-dir outputs/narrative_review_workspace/latest
```

The command writes `narrative_review_workspace.json` and
`narrative_review_workspace.html`. The HTML groups candidates by review status,
links to candidate detail and evidence detail endpoints, shows missing preflight
gates, and lists the supported review actions.

To record an action through the service endpoint before rendering the workspace:

```bash
uv run python scripts/run_narrative_review_workspace.py \
  --service-url http://127.0.0.1:8800 \
  --action approve \
  --candidate-id C_AUTO_3D71C39000 \
  --reviewed-by reviewer-id \
  --review-note "Reviewed source evidence and gates." \
  --idempotency-key review-C_AUTO_3D71C39000-approve
```

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
