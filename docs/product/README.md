# Product Documents

This directory contains product and architecture source documents for Fund Narrative Intelligence.

## Canonical Sources

- [Fund Narrative Intelligence System](./fund-narrative-intelligence-system.html)
- [V1 Implementation Spec](./v1-implementation-spec.md)

## Current Product Definition

The system analyzes a fund through its holdings to identify market narratives, evaluate narrative sustainability, and produce an evidence-backed report. V1 is report-first, monolith-first, and mock-provider capable.

The first implementation loop is:

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

The system must not present output as investment advice or produce buy/sell signals.

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
Eastmoney valuation and financial metrics, and requires financial metrics to be
visible in reports:

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```
