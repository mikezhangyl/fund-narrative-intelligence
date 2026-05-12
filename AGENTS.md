# ECC Operating Mode

This project uses a merged ECC framework:

- ECC's project-local skills, rules, quality discipline, and development workflow.
- Superpower-inspired execution discipline: explicit plans, canonical run directories, worktree criteria, fresh review, and finish-branch decisions.
- Project memory as durable files, not chat memory.

## Startup Context

Before meaningful project work, read in order:

1. `.ecc/framework-state.json`
2. `docs/exec-plans/active/index.md`
3. `docs/memory/project-context.md`
4. `docs/memory/architecture-decisions.md`
5. newest `.ecc/runs/*/run-state.json`, when a run exists
6. any task-specific skill named by the user or implied by the task

## Default Workflow

Use parent execution for small tasks. For complex implementation, framework, or PR-bound tasks:

1. Create or continue a plan under `docs/exec-plans/active/`.
2. Create one canonical `.ecc/runs/<task-run-id>/`.
3. Use exactly one owning Task Agent only when the task qualifies.
4. Do not start nested or same-task role agents after `task_run_id` exists.
5. Run Quality Agent review after implementation when risk warrants it.
6. Record artifacts, findings, decisions, and final disposition in the same run directory.
7. Distill durable knowledge into `docs/memory/` and `.ecc/memory/project/`.

## Agent Policy

- Parent Orchestrator owns all agent starts.
- Task Agent never spawns child agents.
- Quality Agent reviews and writes findings, but does not fix product code.
- Role specialists may be used before a task run exists for planning or scoping.
- Once `task_run_id` exists, same-task role-agent fanout is forbidden.

## Worktree Policy

Default: do not create a worktree.

Create a worktree only for multi-file implementation, risky shared behavior, autonomous workflow changes, parallel work, long-running work, or PR-bound work. Record branch, base commit, head commit, merge base, and final disposition in `.ecc/runs/<task-run-id>/run-state.json`.

## Memory Policy

- Project facts and decisions: `docs/memory/`
- Machine-readable/current framework state: `.ecc/framework-state.json`
- Run-specific temporary state: `.ecc/runs/<task-run-id>/`
- Reusable project memory snippets: `.ecc/memory/project/`
- General cross-project heuristics: `.ecc/memory/global/`
- Do not store secrets, private credentials, or raw sensitive data in memory files.

## Optional Libraries

QA and black-box testing skills may exist under `skills/` as optional library skills. They are not the default operating mode for this project unless the user asks for QA/testing work.

