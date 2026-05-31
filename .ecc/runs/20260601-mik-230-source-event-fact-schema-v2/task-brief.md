# Task Brief

## Linear

- Issue: MIK-230
- Title: [ARCH-P0][R13] Narrative source-event and fact schema v2

## Scope

Define a v2 schema family for heterogeneous narrative source ingestion:
SourceEvent, NarrativeFact, CandidateNarrative, EvidencePack, and SourceQuality.

## Compatibility Boundary

The v2 SourceEvent validator must preserve the existing v1 fixture/trust
workflow by providing an adapter into `source-event-schema-v1`. v2 records remain
candidate/untrusted by default and do not auto-promote trusted facts.

## Verification Notes

- RED: `pytest tests/test_source_schema_v2.py -q` failed on missing
  `scripts.run_source_schema_v2_report`.
- GREEN targeted: `pytest tests/test_source_schema_v2.py -q`.
- Full suite: `pytest -q` passed with 605 passed, 1 skipped.
- Chinese HTML report was checked with Playwright DOM evaluation.
