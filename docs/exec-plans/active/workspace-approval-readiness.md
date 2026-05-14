# Workspace Approval Readiness

## Goal

Make `workspace-snapshot-v1` more directly usable by a future web approval
workspace, without building the UI yet.

## Scope

- Add an explicit `data_source_notice` object to workspace snapshots so web
  screens can show mock, partial, unavailable, or degraded source state without
  re-deriving it from provider layers.
- Add an approval summary under `approval_workflow` that exposes item counts
  and available review actions from the candidate review queue.
- Keep mock disclosure visible in snapshot JSON whenever mock provider layers
  or fallback/degradation are present.

## Non-Goals

- No browser UI or frontend routes.
- No new approval persistence behavior.
- No scoring or provider changes.

## Acceptance

- Workspace snapshot validation requires the new source notice and approval
  summary contract.
- Mock-backed snapshots disclose mock source state at a top-level web-facing
  field.
- Full quality gates pass before merge.
