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

Status: implemented on 2026-05-28 for the local prototype provider slice.

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

Implemented surface:

- `config/narrative_service_contract.yaml` records ownership, endpoint
  expectations, local fallback paths, and trust policy;
- `src/providers/narrative_service.py` exposes `NarrativeDataProvider` and
  `LocalNarrativePrototypeProvider`;
- `scripts/run_fund_holding_exposure_report.py` uses the local prototype
  provider for default `reviewed` registry and mapping inputs;
- `tests/test_narrative_service_provider.py` validates snapshot shape,
  provenance, defensive copying, contract YAML, and report-loader integration.

## Phase 2: Service Project Implementation Request

When a dedicated narrative service project exists, FNI should send it a
documented implementation request instead of copying report code across repos.

Status: request document and FNI conformance probe skeleton implemented on
2026-05-28.

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

Implemented surface:

- `docs/product/narrative-service-implementation-request-2026-05-28.md`
  describes the first service-side build request;
- `scripts/run_narrative_service_conformance_probe.py` checks the endpoint
  envelope declared in `config/narrative_service_contract.yaml`;
- when `NARRATIVE_SERVICE_URL` is absent, the probe writes an explicit
  `not_configured` report instead of pretending the service passed.

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

Implement Phase 3 FNI service consumption:

1. Add an HTTP `NarrativeServiceProvider` behind the same provider-neutral
   interface as `LocalNarrativePrototypeProvider`.
2. Select service-first mode when `NARRATIVE_SERVICE_URL` is configured.
3. Preserve explicit fallback diagnostics when local prototype files are used.
4. Update one report path to disclose `narrative_service`, `local_prototype`,
   or `not_configured` as the narrative fetch mode.
