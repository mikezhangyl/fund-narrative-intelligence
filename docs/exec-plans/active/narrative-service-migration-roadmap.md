# Narrative Service Migration Roadmap

Last updated: 2026-05-28

## Goal

Move narrative production and governance from FNI-local prototypes into an
independent narrative service, while keeping FNI able to generate fund reports
through a stable consumer contract.

## Capability Statement

After this migration, FNI can ask a narrative service for registry snapshots,
stock mappings, evidence packs, trust audit results, and review queue items.
FNI remains the report consumer. The narrative service becomes the owner of
candidate intake, evidence governance, and trust promotion.

## Current Prototype Inputs

FNI currently has these local prototype assets:

- reviewed narrative registry:
  `data/registry/narrative_registry.reviewed.json`
- reviewed stock mapping store:
  `data/registry/stock_narrative_mappings.reviewed.json`
- candidate evidence packs:
  `data/registry/mapping_evidence_packs.v0.json`
- sample candidate intake events:
  `data/fixtures/candidate_narrative_events.v1.json`
- trust audit CLI:
  `scripts/run_narrative_mapping_trust_audit.py`
- mapping evidence pack report CLI:
  `scripts/run_mapping_evidence_pack_report.py`
- candidate narrative intake CLI:
  `scripts/run_candidate_narrative_intake.py`

These prototypes prove the shape of the capability, but they should not become
the final platform ownership model.

## Phase 0: Boundary Documentation

Status: current slice.

Deliverables:

- define the independent service boundary;
- document FNI versus narrative-service responsibilities;
- record target API surfaces;
- update startup memory so future sessions preserve the boundary.

Acceptance:

- `docs/product/narrative-service-boundary.md` exists and is linked from the
  product README;
- this roadmap is linked from the active execution-plan index;
- current memory states that narrative governance is future service-owned.

## Phase 1: Consumer Contract In FNI

Define the contract FNI expects from the future service.

Likely deliverables:

- `config/narrative_service_contract.yaml`;
- typed provider protocol or adapter interface in `src/providers/`;
- local-file fallback provider matching the same interface;
- contract tests using current local prototype files.

Acceptance:

- FNI code reads narratives through a provider-neutral interface;
- local JSON files are one implementation of that interface, not hardcoded
  business truth;
- reports can disclose whether narrative data came from service, local fallback,
  or mock/prototype storage.

## Phase 2: Service Project Implementation Request

When a dedicated narrative service project exists, FNI should send it a
documented implementation request instead of copying report code across repos.

Requested service capabilities:

- registry snapshot endpoint;
- stock mapping endpoint;
- candidate intake endpoint;
- evidence-pack endpoint;
- trust-audit endpoint;
- review-queue endpoint;
- stable envelope with `status`, `provider`, `source`, `warnings`, and
  `trust_metadata`;
- no automatic trusted promotion from raw ingestion.

Acceptance:

- service can reproduce the FNI local prototype outputs through HTTP;
- service returns structured degraded results when source data is missing;
- FNI can run report smoke tests with `NARRATIVE_SERVICE_URL`.

## Phase 3: FNI Service Consumption

Wire FNI reports to prefer the narrative service when configured.

Likely deliverables:

- `NarrativeServiceProvider`;
- `LocalNarrativePrototypeProvider`;
- environment variable such as `NARRATIVE_SERVICE_URL`;
- report-level source diagnostics;
- conformance probe script for live service testing.

Acceptance:

- FNI fund exposure reports can run from narrative service data;
- fallback to local prototype is explicit and disclosed;
- failed service calls do not silently downgrade trusted status.

## Phase 4: Durable Store Migration

Move governance-owned stores out of FNI.

Candidate migrated stores:

- narrative registry;
- stock-to-narrative mappings;
- mapping evidence packs;
- candidate intake event ledger;
- review queue and review decisions;
- trust audit history.

Acceptance:

- FNI no longer owns the authoritative copy of narrative registry or mapping
  data;
- FNI fixture files remain only for tests and offline examples;
- service-side review and audit artifacts can regenerate FNI report inputs.

## Non-Goals

Do not do in this lane yet:

- direct social-media scraping infrastructure;
- browser farms or anti-detect systems;
- LLM-driven trusted writes;
- production database over-design before the contract is stable;
- replacing market-data gateway responsibilities;
- turning FNI into the narrative service runtime.

## Open Questions

- Which repo will host the independent narrative service?
- Should the first service use SQLite/filesystem storage like the gateway
  early phase, or start with PostgreSQL?
- What is the minimum human-review UI surface required before promotion can be
  called trusted?
- Which external sources should be accepted first for narrative discovery:
  Tushare news, company announcements, market-data gateway news briefs, or
  curated manual research?

## Next Recommended Slice

Implement Phase 1 in FNI:

1. Add a provider-neutral narrative data interface.
2. Add a local prototype provider that reads the existing registry, mapping,
   evidence-pack, and intake artifacts.
3. Add a contract YAML describing the service endpoint expectations.
4. Update one report path to consume the provider interface without changing
   report output semantics.

