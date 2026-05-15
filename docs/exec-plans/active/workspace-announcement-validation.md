# Workspace Announcement Validation

## Goal

Reject workspace snapshot bundles when optional announcement payloads drift
between raw and scoring artifacts.

## Scope

- Validate `announcements` raw/scoring equality before writing a workspace
  snapshot.
- Validate `announcement_evidence` raw/scoring equality before writing a
  workspace snapshot.
- Keep the future web loader contract strict without adding frontend UI.

## Non-Goals

- No PDF parsing.
- No new CNINFO provider behavior.
- No report layout changes.

## Acceptance

- Workspace snapshot tests fail first for announcement payload drift.
- Builder rejects mismatched `announcements` and `announcement_evidence`.
- Standard quality gates and V1 acceptance pass.
