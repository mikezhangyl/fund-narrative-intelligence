# V1 Workspace Snapshot Acceptance

## Goal

Extend the default V1 mock acceptance flow so it also builds and validates the
future-web workspace snapshot artifact.

## Scope

- Add `fund_000001_workspace_snapshot.json` to the V1 acceptance expected
  artifact set.
- Build and validate the workspace snapshot during `validate_v1_acceptance.py`.
- Assert the snapshot exposes a top-level mock `data_source_notice` so future
  web surfaces cannot miss mock disclosure.

## Non-Goals

- No frontend implementation.
- No change to the default report pipeline artifact set outside the acceptance
  script's explicit snapshot build step.
- No provider or scoring changes.

## Acceptance

- `python scripts/validate_v1_acceptance.py` builds and validates a workspace
  snapshot.
- Snapshot validation checks mock source disclosure in `data_source_notice`.
- Full quality gates pass before merge.
