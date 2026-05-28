# Product Documents

This directory contains product and architecture source documents for Fund Narrative Intelligence.

## Canonical Sources

- [Fund Narrative Intelligence System](./fund-narrative-intelligence-system.html)
- [V1 Implementation Spec](./v1-implementation-spec.md)
- [Narrative Mapping Methodology v0](./narrative-mapping-methodology-v0.md)
- [Narrative Service Boundary](./narrative-service-boundary.md)
- [Narrative Service Implementation Request](./narrative-service-implementation-request-2026-05-28.md)

## Current Product Definition

The system analyzes a fund through its holdings to identify market narratives, evaluate narrative sustainability, and produce an evidence-backed report. V1 is report-first, monolith-first, and mock-provider capable.

The first implementation loop is:

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

The system must not present output as investment advice or produce buy/sell signals.

Current narrative registry and stock-to-narrative mapping stores are local seed
knowledge, not trusted production knowledge. They are explicitly marked
`trust_status=untrusted_experimental` until a source-and-logic audit proves the
methodology and source chain. The runnable audit entry point is:

```bash
python scripts/run_narrative_mapping_trust_audit.py
```

The first candidate evidence-pack entry point is:

```bash
python scripts/run_mapping_evidence_pack_report.py --symbols 600519,000063,300308
```

Evidence packs are review inputs only. They must remain `candidate_untrusted`
until a human review and methodology audit promotes them.

The candidate narrative intake entry point is:

```bash
python scripts/run_candidate_narrative_intake.py
```

Intake accepts event-style records from future `news`, `announcement`,
`social`, and `manual` sources. It only emits candidate narratives, candidate
stock mappings, and review-queue items; it must not mutate the reviewed or
trusted stores automatically.

Narrative intelligence remains a future independent service boundary. FNI may
keep local prototypes for report integration and contract discovery, but the
future service should own registry lifecycle, stock mapping lifecycle, evidence
packs, candidate intake, trust audits, review queues, and trusted promotion.
The first FNI consumer contract is recorded in
`config/narrative_service_contract.yaml`, with local fallback implemented by
`src/providers/narrative_service.py`. When `NARRATIVE_SERVICE_URL` is
configured, FNI can now use `NarrativeServiceProvider` in service-first mode
with explicit local fallback through `FallbackNarrativeDataProvider`.

The first engineering acceptance command is:

```bash
python scripts/validate_v1_acceptance.py
```

It must generate fund `000001`, validate generated artifact contracts, build and
validate a workspace snapshot, confirm mock data is visibly disclosed, and
produce raw JSON, scoring JSON, review queue, source table, manifest, Markdown
report, HTML report, signal trace, and workspace snapshot artifacts.

V1 can also list available mock fixtures:

```bash
python -m src.main --list-fixtures
```

And run all local mock scenarios:

```bash
python -m src.main --run-all-fixtures
```

Future web loading is prepared through:

```bash
python -m src.main --build-workspace-snapshot outputs/
python -m src.main --validate-workspace-snapshot outputs/fund_000001_workspace_snapshot.json
python -m src.main --validate-signal-trace outputs/fund_000001_signal_trace.json
```

The workspace snapshot includes top-level `data_source_notice`, `data_layers`,
`signal_trace`, and `approval_workflow` fields so a future web UI can display
mock/partial source warnings, provider payload availability/counts, score
provenance, and review-action state without rebuilding them from lower-level
artifacts.

The strict reviewed-mapping enriched acceptance path now uses explicit
Eastmoney valuation and financial metrics, and requires both valuation snapshots
and financial metrics to be visible in reports:

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```
