---
name: project-bootstrap
description: Use when starting this project, recovering project context, creating the first execution plan, or deciding how to apply the merged ECC + Superpower + memory framework.
---

# Project Bootstrap

Use this skill at project start and when context is unclear.

## Read First

1. `.ecc/framework-state.json`
2. `AGENTS.md`
3. `docs/exec-plans/active/index.md`
4. `docs/memory/project-context.md`
5. `docs/memory/architecture-decisions.md`

## Bootstrap Loop

1. Clarify the project goal and first deliverable.
2. Create or update an execution plan under `docs/exec-plans/active/`.
3. Decide whether work qualifies for `ecc-task-subagent-workflow`.
4. Create `.ecc/runs/<task-run-id>/` for complex work.
5. Keep durable decisions in `docs/memory/`.
6. Keep run-specific facts in `.ecc/runs/<task-run-id>/`.

## Defaults

- Do not start with QA-only workflow unless the user asks for testing.
- Do not start sub-agents before task boundaries are clear.
- Do not create a worktree for small planning or documentation edits.
- Prefer full scaffold with progressive activation.

