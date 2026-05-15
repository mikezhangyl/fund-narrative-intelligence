# Signal Trace Artifact

## Goal

Emit a dedicated, validated artifact that explains which signal events feed each
narrative score, with source provenance preserved for future web visualization.

## Scope

- Build `fund_<code>_signal_trace.json` during normal pipeline runs.
- Include per-narrative dimension traces from scoring outputs and signal events.
- Preserve source, provider, source URL, stock code, event date, confidence, and
  whether the trace is from mock-backed or provider-derived data.
- Add the artifact to the manifest and workspace snapshot.
- Validate it through artifact-contract and workspace-snapshot validation.

## Non-Goals

- No web UI yet.
- No new scoring weights or score recalculation.
- No LLM-generated signal explanations.

## Acceptance

- Pipeline tests assert the signal trace artifact exists and is in the manifest.
- Validator tests reject malformed signal trace artifacts.
- V1 acceptance and reviewed-mapping enriched acceptance still pass.
- Mock-backed baseline traces remain explicitly marked through source URLs and
  provider-foundation disclosure.
