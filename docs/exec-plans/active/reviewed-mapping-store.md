# Reviewed Mapping Store

## Goal

Add an optional stock-to-narrative mapping mode that loads explicit mappings
from a file-backed reviewed mapping store instead of static fixtures or runtime
registry-rule derivation.

## Scope

- Keep default fixture mapping behavior unchanged.
- Add `--stock-mapping-mode reviewed` for single report runs.
- Add a default reviewed mapping store at
  `data/registry/stock_narrative_mappings.reviewed.json`.
- Add `--stock-mappings-path` for alternate reviewed mapping snapshots.
- Mark the `Stock Mappings` provider-foundation layer as non-mock
  `reviewed-mapping-store` in reviewed mode.
- Add a strict live acceptance command for the enriched path with reviewed
  registry, reviewed mappings, provider-derived intelligence, announcements,
  and market quotes.

## Non-Goals

- Do not remove fixture or registry-rule mapping modes.
- Do not build web approval UI in this slice.
- Do not require reviewed mapping live acceptance in CI.

## Acceptance

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```

Expected result:

- Raw/scoring JSON include `stock_mapping_mode=reviewed`.
- Selected mappings use `reviewed_mapping`, not `fixture_rule` or
  `registry_term_rule`.
- Provider foundation shows `Stock Mappings` from `reviewed-mapping-store`,
  with `is_mock=false`.
- Reports disclose the reviewed mapping source URL with content hash and do not
  label stock mappings as a Mock fixture.
