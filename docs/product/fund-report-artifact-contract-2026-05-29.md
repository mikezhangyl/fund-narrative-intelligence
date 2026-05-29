# Fund Report Artifact Contract - 2026-05-29

## Scope

This document records the Round 2 MIK-65 contract for fund intelligence report
packs. The machine-readable contract is
`config/fund_report_artifact_contract.json`.

## Manifest

Report packs use `pipeline-artifact-manifest-v1`. The manifest must include:

- `run_id`
- `generated_at`
- `fund_code`
- `as_of_date`
- `provider_mode`
- `data_quality`
- `source_modes`
- `warning_counts`
- `trust_states`
- `provider_foundation`
- `degradation_events`
- `artifacts`

The generator validates the manifest before writing it. Workspace snapshot
building also validates the manifest and fails if any declared artifact is
missing.

## Naming

Generated artifacts follow these names:

- `fund_{fund_code}_raw.json`
- `fund_{fund_code}_scoring.json`
- `fund_{fund_code}_review_queue.json`
- `fund_{fund_code}_source_table.json`
- `fund_{fund_code}_signal_trace.json`
- `fund_{fund_code}_manifest.json`
- `fund_{fund_code}_report.md`
- `fund_{fund_code}_report.html`
- `fund_{fund_code}_workspace_snapshot.json`

## Reader Surface

The canonical reader surface is HTML. The HTML report links to the underlying
JSON artifacts: raw, scoring, review queue, source table, and signal trace.

## Missing Data And Generated Output Policy

Missing gateway or Narrative Service data is represented through provider
foundation layers, degradation events, and manifest `warning_counts`.

All report artifacts are generated output only. The contract config and this
document are source-controlled.

No report pack writes trusted promotion state. `trust_states.trusted_promotion`
must remain `disabled`.
