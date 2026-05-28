# Narrative Store Migration Checklist

Last updated: 2026-05-28

## Purpose

This checklist prepares the move from FNI-local narrative prototype files to an
independent authoritative Narrative Service.

It does not delete local files. Until the service passes conformance and
provider smoke, FNI local stores remain fallback/test fixtures.

## Current Local Stores

These files are currently local FNI prototype/fallback stores:

- `data/registry/narrative_registry.reviewed.json`
- `data/registry/stock_narrative_mappings.reviewed.json`
- `data/registry/mapping_evidence_packs.v0.json`
- `data/fixtures/candidate_narrative_events.v1.json`

Current trust status:

- reviewed registry: `untrusted_experimental`
- reviewed stock mappings: `untrusted_experimental`
- mapping evidence packs: `candidate_untrusted`
- candidate intake events: test/sample event records

## Target Ownership

The independent Narrative Service should become authoritative owner of:

- narrative registry;
- stock-to-narrative mappings;
- mapping evidence packs;
- candidate intake event ledger;
- review queue;
- review decisions;
- trust audit history;
- trusted promotion policy.

FNI should retain:

- consumer contract;
- report rendering;
- conformance and provider smoke probes;
- local fallback fixtures for offline tests;
- source diagnostics in reports.

## Pre-Migration Requirements

Before service ownership can be treated as authoritative:

- `config/narrative_service_contract.yaml` matches the service API;
- `python scripts/run_narrative_service_conformance_probe.py` passes against
  `NARRATIVE_SERVICE_URL`;
- `python scripts/run_narrative_service_provider_smoke.py` reports
  `source=narrative_service`;
- fund holding exposure report can run with narrative source
  `narrative_service`;
- service responses preserve current untrusted/candidate trust states;
- fallback behavior is still visible when the service is unreachable;
- no automatic ingestion path promotes data to trusted status.

## Migration Steps

1. Import local FNI prototype stores into the Narrative Service as untrusted or
   candidate records.
2. Run trust audit in the service and persist audit result as service-owned
   state.
3. Run FNI conformance probe against the service.
4. Run FNI provider smoke against the service.
5. Run one FNI fund holding exposure report with `NARRATIVE_SERVICE_URL` and
   confirm HTML/JSON disclose `narrative_service`.
6. Mark FNI local stores as fallback fixtures in docs and tests.
7. Stop adding new authoritative narrative records directly to FNI local stores.

## Do Not Do Yet

- Do not delete FNI local files before service smoke and report acceptance pass.
- Do not treat migrated records as trusted merely because they live in the
  service.
- Do not allow service ingestion to write trusted records without human review.
- Do not build social crawler infrastructure in this migration slice.
- Do not make FNI the production runtime for the Narrative Service.

## Acceptance

Migration preparation is complete when:

- ownership boundary is documented;
- local stores are explicitly labeled fallback/test fixtures;
- service readiness checks are listed and runnable;
- future agents can tell which repo owns narrative truth after service launch.

