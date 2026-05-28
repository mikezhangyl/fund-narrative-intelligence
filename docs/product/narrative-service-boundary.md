# Narrative Service Boundary

Last updated: 2026-05-28

## Conclusion

Narrative intelligence should remain an independent service boundary.

The current FNI repository may keep local prototypes for contract discovery,
consumer validation, and report integration, but it should not become the final
owner of narrative registry storage, mapping governance, candidate intake, or
trust promotion workflows.

## Why This Boundary Exists

FNI answers a consumer question:

> Given a fund and its holdings, what market narratives does the fund appear to
> carry, and how reliable is the supporting evidence?

The narrative service answers a platform question:

> Which narratives exist, which stocks map to them, what evidence supports that
> relationship, and which records are trusted enough to publish?

These are different ownership problems. Keeping them separate prevents report
code from becoming the long-term source of truth for narrative knowledge.

## FNI Responsibilities

FNI owns:

- fund report workflows;
- fund holding exposure, fund comparison, and narrative exposure matrix outputs;
- consumer-side provider contracts and fallback behavior;
- HTML/JSON report rendering;
- data-gap and trust-status disclosure in reports;
- validation that a narrative API can support report workflows;
- temporary local fixtures and prototype files while the service contract is
  still being discovered.

FNI may create candidate artifacts for review, but those artifacts are consumer
prototypes unless and until they are migrated to the narrative service.

## Narrative Service Responsibilities

The independent narrative service should own:

- narrative registry lifecycle;
- stock-to-narrative mapping lifecycle;
- candidate narrative intake from news, announcements, social sources, and
  manual research;
- mapping evidence packs;
- source provenance and citation chains;
- trust audit and promotion policy;
- review queues and human approval workflow;
- durable storage for candidate, reviewed, rejected, and trusted records;
- provider-neutral APIs consumed by FNI and other future analysis products.

## Current FNI Prototype Inventory

These files are useful prototypes, not final ownership boundaries:

- `data/registry/narrative_registry.reviewed.json`
- `data/registry/stock_narrative_mappings.reviewed.json`
- `data/registry/mapping_evidence_packs.v0.json`
- `data/fixtures/candidate_narrative_events.v1.json`
- `scripts/run_narrative_mapping_trust_audit.py`
- `scripts/run_mapping_evidence_pack_report.py`
- `scripts/run_candidate_narrative_intake.py`

Current reviewed registry and mapping records are explicitly
`trust_status=untrusted_experimental`. In this project, `reviewed` currently
means the records are structurally usable by the pipeline, not that the source
chain and mapping logic are production-trusted.

## Target API Surface

The future narrative service should expose provider-neutral endpoints similar
to:

- `GET /api/v1/narratives/registry`
- `GET /api/v1/narratives/mappings`
- `POST /api/v1/narratives/intake/events`
- `GET /api/v1/narratives/candidates`
- `GET /api/v1/narratives/evidence-packs`
- `GET /api/v1/narratives/trust-audits/latest`
- `GET /api/v1/narratives/review-queue`

FNI should consume these endpoints through a small provider layer, with local
prototype files used only as an explicit fallback during migration.

## Trust Policy

Automatic ingestion may create:

- candidate narratives;
- candidate stock mappings;
- candidate evidence packs;
- review queue items.

Automatic ingestion must not create:

- trusted narratives;
- trusted stock mappings;
- silently promoted reviewed records;
- report-visible claims without source and trust disclosure.

Promotion from candidate to trusted requires explicit review, source evidence,
mapping rationale, exclusion criteria, and audit output.

## Non-Goals For FNI

FNI should not own:

- long-term narrative database schema design;
- review UI workflow;
- social-media crawler orchestration;
- trusted mapping promotion policy;
- source-wide narrative discovery scheduling;
- LLM-driven durable writes.

FNI can keep small compatibility shims and report-oriented probes, but new
durable narrative capabilities should be expressed as service requirements.

## Near-Term Operating Rule

Until the narrative service exists, FNI continues to run local prototypes so the
report pipeline can evolve. Each new narrative prototype should be shaped as a
future service contract, not as permanent FNI-owned storage.

