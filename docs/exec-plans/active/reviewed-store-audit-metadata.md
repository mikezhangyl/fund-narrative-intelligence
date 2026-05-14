# Reviewed Store Audit Metadata

## Goal

Add explicit review/audit metadata to reviewed registry and reviewed mapping
stores so future web approval screens can display who approved what and when.

## Scope

- Add store-level `review_metadata` to reviewed registry and mapping files.
- Require reviewed registry active narratives to include non-empty
  `reviewed_by` and `reviewed_at`.
- Require candidate narratives to keep candidate status without pretending to be
  approved.
- Add per-mapping `review` metadata to reviewed mapping records.
- Make reviewed providers reject missing or invalid review metadata.
- Keep fixture providers and default fixture mode unchanged.

## Non-Goals

- Do not build the web approval UI in this slice.
- Do not change review-action persistence output format yet.
- Do not require reviewed metadata in mock fixtures.

## Acceptance

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```

Expected result:

- Reviewed registry and mapping stores pass provider metadata validation.
- Live enriched reviewed-mapping acceptance still passes.
- Artifacts continue to disclose reviewed store source URLs with content hashes.
