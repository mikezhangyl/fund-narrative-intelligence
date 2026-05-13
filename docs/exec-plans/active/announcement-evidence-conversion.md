# Announcement Evidence Conversion Execution Plan

## Purpose

Add a deterministic conversion layer that turns structured announcement metadata into V1 evidence records.

## Scope

- Add an announcement-to-evidence module under `src/modules/evidence/`.
- Map announcement stock codes through existing stock-to-narrative mappings.
- Classify announcement titles/categories with conservative V1 keyword rules.
- Preserve data-quality and mapping-confidence effects in generated evidence confidence.
- Keep the converter optional and outside the default report pipeline.

## Out Of Scope

- Downloading or parsing announcement PDFs.
- Mutating the narrative registry or signal schema.
- Wiring CNINFO evidence into default report generation.
- Treating announcement metadata as investment advice or trading signal output.

## Acceptance

- Unit tests cover supporting, risk, multi-narrative, unmapped, and skipped announcement cases.
- Generated evidence validates against the existing evidence payload contract.
- Full lint, test, coverage, compile, and live smoke gates pass.

## Status

Implemented, verified, and ready to merge.

## Run Record

- `.ecc/runs/20260513-announcement-evidence-conversion/`
