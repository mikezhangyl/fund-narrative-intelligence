# Broad Industry Mapping Flags Execution Plan

## Purpose

Make broad industry-only fallback mappings visible as lower-precision mappings that need registry curation.

## Scope

- Detect `registry_term_rule` mappings where every matched term appears only in the holding's industry field.
- Lower confidence for single broad industry-only fallback mappings.
- Mark affected mappings with `needs_review` and `precision_flag: broad_industry_fallback`.
- Emit `mapping_precision_flags` entries with `recommended_action: curation_review`.
- Keep `multi_match_fallback` as the higher-priority flag when multiple narratives match one holding.

## Non-Goals

- Removing broad industry terms from the registry.
- Changing narrative aggregation weights.
- Adding a manual curation UI.

## Acceptance

- Unit tests cover broad industry-only fallback precision.
- Pipeline tests cover raw/scoring/report output.
- Existing multi-match precision tests remain stable.
- Full quality gates and live smoke commands pass.

## Run Record

- `.ecc/runs/20260514-broad-industry-mapping-flags/`
