# Implementation Notes

## Summary

Implemented a mock-first Python V1 pipeline for Fund Narrative Intelligence.

The pipeline now:

- accepts `--fund-code`, `--provider-mode`, and `--output-dir`;
- loads deterministic local JSON fixtures;
- keeps a narrative registry and stock-to-narrative mappings;
- aggregates holdings into fund narrative exposure;
- scores narratives across five dimensions using decayed signal events;
- writes raw JSON, scoring JSON, Markdown report, and HTML report artifacts;
- degrades `--provider-mode real` to mock in V1 with explicit degradation events.

## Design Choices

- Runtime dependencies are standard-library only.
- `pytest` is used for tests.
- Generated `outputs/` are ignored by git.
- V1 confidence is deliberately lower for mock data because `data_quality=mock` applies a confidence penalty.
- Report language explicitly avoids investment advice.

## Deviations

- No child Task Agent or Quality Agent was spawned because the active Codex tool policy only permits sub-agents when the user explicitly asks for delegated or parallel agent work.
- A parent quality review was recorded in the run directory instead.
