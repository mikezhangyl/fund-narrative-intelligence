# Provider Foundation Review Metadata

## Goal

Expose reviewed store audit metadata in provider foundation layers so future web
source tables can show approval provenance without reparsing source store files.

## Scope

- Preserve optional `review_metadata` on provider-foundation layers.
- Add reviewed registry and reviewed mapping store metadata to their provider
  layers.
- Keep source URLs with content hashes unchanged.
- Keep default mock/fixture providers unchanged.

## Non-Goals

- Do not build web UI in this slice.
- Do not change scoring or report interpretation.
- Do not add review metadata requirements to non-reviewed providers.

## Acceptance

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```

Expected result:

- `provider_foundation.layers.narrative_registry.review_metadata` is present.
- `provider_foundation.layers.stock_mappings.review_metadata` is present.
- Existing reviewed-mapping enriched acceptance still passes.
