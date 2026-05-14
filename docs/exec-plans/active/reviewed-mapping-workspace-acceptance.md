# Reviewed Mapping Workspace Acceptance

## Goal

Make the strict reviewed-mapping enriched acceptance path produce and validate
the future-web workspace snapshot artifact.

## Scope

- Build `fund_<code>_workspace_snapshot.json` during reviewed-mapping enriched
  acceptance.
- Validate the generated workspace snapshot through the existing CLI contract.
- Keep the acceptance path strict: reviewed registry, reviewed mappings,
  provider-derived evidence/signals, market quotes, CNINFO announcements, and
  news evidence remain required.

## Non-Goals

- No frontend implementation.
- No provider or scoring changes.
- No changes to default mock V1 acceptance behavior.

## Acceptance

- Reviewed-mapping acceptance script calls `--build-workspace-snapshot` and
  `--validate-workspace-snapshot`.
- Acceptance output reports the workspace snapshot artifact.
- Targeted and full quality gates pass before merge.
