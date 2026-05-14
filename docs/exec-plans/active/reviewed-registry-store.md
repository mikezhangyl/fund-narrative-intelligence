# Reviewed Registry Store

## Goal

Add an optional Narrative Registry mode that loads reviewed narrative
definitions from a file-backed registry store instead of the mock fixture
provider.

## Scope

- Keep default fixture registry behavior unchanged.
- Add `--narrative-registry-mode reviewed` for single report runs.
- Add a default reviewed store at `data/registry/narrative_registry.reviewed.json`.
- Mark the `Narrative Registry` provider-foundation layer as non-mock when the
  reviewed store is used.
- Emit `narrative_registry_mode` in raw and scoring artifacts.
- Add a strict live acceptance command for the enriched path with reviewed
  registry, registry-rule mapping, and provider-derived intelligence.

## Non-Goals

- Do not build web approval UI in this slice.
- Do not remove fixture mode.
- Do not change candidate approval semantics.
- Do not add reviewed registry live acceptance to CI, because the enriched path
  depends on live provider availability.

## Acceptance

```bash
python scripts/validate_reviewed_registry_enriched_acceptance.py --output-dir outputs/reviewed_registry_enriched_161725
```

Expected result:

- Raw/scoring JSON include `narrative_registry_mode=reviewed`.
- Provider foundation shows `Narrative Registry` from
  `reviewed-registry-store`, with `is_mock=false`.
- Stock mappings use `registry_term_rule`.
- Base evidence and signals are provider-derived, not fixture-backed.
- Reports disclose the reviewed registry source URL and do not label the
  registry as a Mock fixture.
