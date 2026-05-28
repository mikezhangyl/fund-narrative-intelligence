# Stock Narrative Service Bootstrap Prompt

Last updated: 2026-05-28

## Recommended Project Name

`stock-narrative-service`

## Project Role

This project should be an independent Narrative Service, not part of FNI and
not part of the market-data gateway.

Implementation update: this service is now implemented as an in-repo monorepo
subservice at `services/stock-narrative-service/`. It still keeps the HTTP
service boundary; FNI should consume it through `NARRATIVE_SERVICE_URL`, not by
importing service internals.

Target service split:

- `stock-data-gateway`: market data and external data-source access.
- `stock-narrative-service`: narrative registry, stock mappings, evidence,
  candidate intake, review queue, trust audit, and promotion governance.
- `fund-narrative-intelligence`: report consumer that calls the narrative
  service and generates fund-facing analysis.

Current in-repo start command:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8800
```

## First Version Goal

Build the smallest HTTP service that FNI can call through:

```bash
NARRATIVE_SERVICE_URL=http://127.0.0.1:<port>
```

The first version should pass FNI's existing checks:

```bash
uv run python scripts/run_narrative_service_conformance_probe.py
uv run python scripts/run_narrative_service_provider_smoke.py
```

Do not build AI narrative discovery, social scraping, browser automation, or a
complex review UI in the first slice.

## Source Documents From FNI

Read these files from:

`/Users/mikezhang/Coding/AI-Learning/fund-narrative-intelligence`

- `docs/product/narrative-service-implementation-request-2026-05-28.md`
- `config/narrative_service_contract.yaml`
- `docs/product/narrative-store-migration-checklist.md`
- `docs/product/narrative-service-boundary.md`

These are the current consumer contract and migration rules from FNI.

## Required API Endpoints

Implement these endpoints under `/api/v1/narratives`:

```text
GET  /api/v1/narratives/registry
GET  /api/v1/narratives/mappings
POST /api/v1/narratives/intake/events
GET  /api/v1/narratives/candidates
GET  /api/v1/narratives/evidence-packs
GET  /api/v1/narratives/trust-audits/latest
GET  /api/v1/narratives/review-queue
```

Every endpoint must return this normalized envelope:

```json
{
  "status": "available",
  "source": "narrative_service",
  "provider": "stock-narrative-service",
  "provider_version": "v0",
  "data": {},
  "warnings": [],
  "trust_metadata": {}
}
```

If data is missing or partially available, return a structured degraded
response. Do not return empty success silently.

## Initial Data

Seed the service from FNI's current local prototype files:

```text
data/registry/narrative_registry.reviewed.json
data/registry/stock_narrative_mappings.reviewed.json
data/registry/mapping_evidence_packs.v0.json
data/fixtures/candidate_narrative_events.v1.json
```

Important: importing these files into the service does not make them trusted.
Preserve the existing trust states:

- `untrusted_experimental`
- `candidate_untrusted`

## Storage Guidance

For the first version, use simple local storage:

- JSON files, or
- SQLite.

Do not over-design PostgreSQL, queue workers, crawler orchestration, or
distributed jobs until the HTTP contract passes FNI validation.

## Trust Rules

Automatic ingestion may create:

- candidate narratives;
- candidate stock mappings;
- candidate evidence packs;
- review queue items.

Automatic ingestion must not create:

- trusted narratives;
- trusted stock mappings;
- silently promoted reviewed records.

Promotion to trusted status requires:

- human review;
- source evidence;
- mapping rationale;
- exclusion criteria;
- trust audit.

## Acceptance From FNI

After the service starts locally, go to FNI and run:

```bash
cd /Users/mikezhang/Coding/AI-Learning/fund-narrative-intelligence

NARRATIVE_SERVICE_URL=http://127.0.0.1:<port> \
uv run python scripts/run_narrative_service_conformance_probe.py

NARRATIVE_SERVICE_URL=http://127.0.0.1:<port> \
uv run python scripts/run_narrative_service_provider_smoke.py
```

Then run one FNI report and verify that its JSON/HTML shows:

```text
narrative_source = narrative_service
```

## Copy-Paste Prompt For The New Project

```text
We are starting a new independent project named stock-narrative-service.

This service is not fund-narrative-intelligence and not stock-data-gateway.
Its job is to become the authoritative Narrative Service for narrative
registry, stock-to-narrative mappings, mapping evidence packs, candidate
intake, review queue, trust audit, and trusted promotion governance.

Use the existing FNI project as the consumer contract source:

/Users/mikezhang/Coding/AI-Learning/fund-narrative-intelligence

Read these files first:

- docs/product/narrative-service-implementation-request-2026-05-28.md
- config/narrative_service_contract.yaml
- docs/product/narrative-store-migration-checklist.md
- docs/product/narrative-service-boundary.md

Build only the first Can-Do service slice:

1. Create a minimal HTTP API service.
2. Implement these endpoints:
   GET  /api/v1/narratives/registry
   GET  /api/v1/narratives/mappings
   POST /api/v1/narratives/intake/events
   GET  /api/v1/narratives/candidates
   GET  /api/v1/narratives/evidence-packs
   GET  /api/v1/narratives/trust-audits/latest
   GET  /api/v1/narratives/review-queue
3. Every endpoint must return the normalized envelope required by FNI:
   status, source, provider, provider_version, data, warnings, trust_metadata.
4. Seed initial local service data from FNI's current prototype files:
   data/registry/narrative_registry.reviewed.json
   data/registry/stock_narrative_mappings.reviewed.json
   data/registry/mapping_evidence_packs.v0.json
   data/fixtures/candidate_narrative_events.v1.json
5. Preserve current trust states. Do not mark migrated records trusted.
6. Use JSON files or SQLite for first version storage. Do not over-engineer.
7. Implement candidate intake as review-only. It may create candidates and
   review queue items, but must not create trusted records.
8. Add tests for every endpoint and for trust-state preservation.
9. Start the service locally and verify it from FNI by running:

   cd /Users/mikezhang/Coding/AI-Learning/fund-narrative-intelligence

   NARRATIVE_SERVICE_URL=http://127.0.0.1:<port> \
   uv run python scripts/run_narrative_service_conformance_probe.py

   NARRATIVE_SERVICE_URL=http://127.0.0.1:<port> \
   uv run python scripts/run_narrative_service_provider_smoke.py

10. Do not implement AI narrative discovery, social scraping, browser
    automation, production review UI, or complex database architecture in this
    first slice.

The definition of done is: FNI conformance probe passes, FNI provider smoke
returns source=narrative_service, and at least one FNI report can disclose
narrative_source=narrative_service.
```
