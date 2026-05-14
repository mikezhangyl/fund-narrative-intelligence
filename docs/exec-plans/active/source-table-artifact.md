# Source Table Artifact

## Goal

Emit a dedicated source-table JSON artifact from each fund pipeline run so a
future web workspace can render source/provenance rows without reconstructing
them from raw scoring payloads.

## Scope

- Add `fund_<code>_source_table.json` to generated pipeline artifacts.
- Include fund identity, as-of date, provider-foundation layers, source URLs,
  data quality, mock flags, optional review metadata, and degradation events.
- Reference the artifact from `fund_<code>_manifest.json`.
- Validate source-table contracts through `--validate-artifact-contracts` in both
  manifest-referenced and standalone directory-discovery modes.
- Keep the artifact directly renderable by a future web source/provenance table.

## Non-Goals

- Do not build the future web UI in this slice.
- Do not add approval interactions to the CLI.
- Do not change scoring, narrative mapping, or report interpretation.

## Acceptance

```bash
python scripts/validate_v1_acceptance.py
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
python -m src.main --validate-artifact-contracts outputs/reviewed_mapping_enriched_161725
```

Expected result:

- The V1 artifact set includes `fund_000001_source_table.json`.
- The manifest references the source-table artifact with JSON format metadata.
- Source-table contract validation rejects identity mismatches, malformed
  provider-foundation layers, missing render fields, duplicate layers, and
  layer/foundation drift.
- Reviewed store `review_metadata` remains visible in source-table layers.
