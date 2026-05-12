---
name: finish-branch
description: Use before closing, merging, keeping, discarding, or PR-ing a worktree or branch; records final disposition and prevents losing unreferenced artifacts.
---

# Finish Branch

Use when a branch or worktree is ready to close.

## Checks

1. Read the relevant `.ecc/runs/<task-run-id>/run-state.json`.
2. Verify final `head_commit` and reviewed snapshot.
3. Verify task and quality artifacts are referenced.
4. Check for uncommitted changes.
5. Record final decision in `.ecc/runs/<task-run-id>/decisions/finish-branch-decision.md`.

## Allowed Decisions

- `keep`
- `merge`
- `pr`
- `discard`

Never discard a worktree with uncommitted changes or unreferenced artifacts unless the decision file explicitly records approval and rationale.

