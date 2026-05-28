# Narrative Service Implementation Request

Date: 2026-05-28

## Purpose

Build an independent narrative service that can replace FNI-local narrative
prototype files as the authoritative owner of narrative registry, stock
mapping, evidence packs, candidate intake, trust audit, and review queue
state.

FNI will remain a consumer. It should call the service through
`NARRATIVE_SERVICE_URL` and fall back to local prototype files only when the
service is not configured or explicitly unavailable.

## Source Documents

- Boundary: `docs/product/narrative-service-boundary.md`
- Consumer contract: `config/narrative_service_contract.yaml`
- Migration roadmap:
  `docs/exec-plans/active/narrative-service-migration-roadmap.md`
- Current local provider prototype: `src/providers/narrative_service.py`

## Required API Shape

Use stable REST resources under `/api/v1/narratives`.

Required endpoints:

- `GET /api/v1/narratives/registry`
- `GET /api/v1/narratives/mappings`
- `POST /api/v1/narratives/intake/events`
- `GET /api/v1/narratives/candidates`
- `GET /api/v1/narratives/evidence-packs`
- `GET /api/v1/narratives/trust-audits/latest`
- `GET /api/v1/narratives/review-queue`

Each endpoint should return a provider-neutral envelope with:

- `status`
- `source`
- `provider`
- `provider_version`
- `data`
- `warnings`
- `trust_metadata`

Use structured degraded results for partial failure. Do not return empty
success when upstream evidence, registry rows, or mapping rows cannot be
loaded.

## Initial Data Migration Inputs

The first service implementation can ingest the current FNI local prototypes:

- `data/registry/narrative_registry.reviewed.json`
- `data/registry/stock_narrative_mappings.reviewed.json`
- `data/registry/mapping_evidence_packs.v0.json`
- `data/fixtures/candidate_narrative_events.v1.json`

These files are not trusted production knowledge. Preserve their trust status
as `untrusted_experimental` or `candidate_untrusted`.

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

Trusted promotion requires:

- human review;
- source evidence;
- mapping rationale;
- exclusion criteria;
- trust audit.

## FNI Conformance Probe

FNI now provides:

```bash
python scripts/run_narrative_service_conformance_probe.py
```

Without `NARRATIVE_SERVICE_URL`, the probe writes `not_configured`. Once the
service exists, set:

```bash
NARRATIVE_SERVICE_URL=http://127.0.0.1:<port>
```

The probe will check all endpoints declared in
`config/narrative_service_contract.yaml` and verify that each response exposes
the required envelope fields.

## Non-Goals

Do not implement in the first service slice:

- social-media scraping infrastructure;
- browser automation;
- trusted automatic promotion;
- LLM-written durable truth;
- market-data gateway replacement;
- FNI report rendering.

## Acceptance

The first service slice is acceptable when:

- all required endpoints return the normalized envelope;
- imported FNI prototype records preserve their untrusted status;
- intake events create only candidate/review artifacts;
- `python scripts/run_narrative_service_conformance_probe.py` passes when
  `NARRATIVE_SERVICE_URL` points at the service;
- FNI reports can continue using local fallback until service consumption is
  wired in the next FNI slice.

