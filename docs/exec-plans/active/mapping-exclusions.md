# Mapping Exclusions Execution Plan

## Purpose

Prevent known-bad fallback mapping candidates from entering narrative aggregation and scoring while keeping the exclusion visible for review.

## Scope

- Add a local `mapping_exclusions.json` fixture.
- Load exclusions through the mock intelligence provider set.
- Apply exclusions to fallback mapping candidates only.
- Emit `excluded_mapping_candidates` in raw/scoring JSON, reports, and real-smoke summaries.
- Print excluded candidate counts in real-smoke CLI output.

## Non-Goals

- Creating new narratives for excluded stocks.
- Applying exclusions to explicit curated fixture mappings.
- Changing real-smoke pass/fail thresholds.

## Acceptance

- Tests cover mapping, provider, pipeline, report, real-smoke summary, and CLI behavior.
- Real smoke passes with excluded candidates visible.
- Full quality gates and announcement smoke pass.

## Run Record

- `.ecc/runs/20260514-mapping-exclusions/`
