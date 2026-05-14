# Workspace Snapshot Loader

## Goal

Create a server-side workspace snapshot contract that future web screens can
load directly from a generated artifact bundle without guessing file names or
re-joining raw, scoring, review queue, source table, and report artifacts.

## Scope

- Add a workspace snapshot builder for a manifest file or output directory.
- Emit `fund_<code>_workspace_snapshot.json` with identity, artifact manifest,
  provider foundation, source table, review queue, narrative summaries, report
  paths, and web workflow readiness metadata.
- Add CLI commands to build and validate workspace snapshot artifacts.
- Validate that snapshot identity and embedded contracts match the source
  artifact bundle.

## Non-Goals

- Do not build browser UI in this slice.
- Do not add approval mutations or persistence flows beyond existing review
  action commands.
- Do not change scoring, narrative mapping, provider calls, or report text.

## Acceptance

```bash
python -m src.main --build-workspace-snapshot outputs/reviewed_mapping_enriched_161725
python -m src.main --validate-workspace-snapshot outputs/reviewed_mapping_enriched_161725/fund_161725_workspace_snapshot.json
```

Expected result:

- The snapshot validates as `workspace-snapshot-v1`.
- The snapshot includes `approval_workflow.status = ready_for_future_web`.
- The snapshot embeds source-table rows and candidate review queue objects.
- Snapshot validation rejects identity drift and missing source table/review
  queue contracts.
