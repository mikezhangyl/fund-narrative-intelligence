# V1 Data Layers Acceptance

## Goal

Make the V1 acceptance script explicitly verify workspace snapshot
`data_layers` mock disclosure so future web data-tab contracts cannot regress
silently.

## Scope

- Add explicit V1 acceptance checks for `workspace-data-layers-v1`.
- Require mock baseline data layers to expose at least one `mock://fixtures/`
  source URL.
- Keep generic schema validation in `src.validation`; this slice adds
  acceptance-level business checks only.

## Non-Goals

- No workspace snapshot schema changes.
- No report or scoring changes.

## Acceptance

- A mutated workspace snapshot with non-mock data-layer source URL fails V1
  acceptance validation.
- Standard quality gates and V1 acceptance pass.
