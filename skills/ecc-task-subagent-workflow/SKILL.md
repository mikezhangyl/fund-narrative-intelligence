---
name: ecc-task-subagent-workflow
description: Use for complex ECC implementation tasks that need one owning Task Agent, optional later Quality Agent review, runtime-checkable anti-nesting rules, one canonical .ecc run directory, and scoped worktree usage. Trigger for multi-file features, shared data/cache changes, autonomous workflow changes, long-running implementation, parallel implementation, or PR-bound work. Do not trigger for reading code, explanations, small docs edits, immutable research artifacts, or low-risk single-file fixes.
---

# ECC Task Sub-Agent Workflow

Use this skill only when the task is large, risky, autonomous, parallel, long-running, or PR-bound. Parent execution is the default for routine work.

For the full run-state, handoff, Quality Agent, and manifest contracts, read `references/run-contract.md` only when creating artifacts, validating a run, or changing `scripts/ecc_task_run.py`.

## Trigger

Use this workflow when at least one condition is true:

- multi-file implementation touching shared behavior
- data/cache/provider contract changes
- autonomous agent or harness workflow changes
- work likely to span multiple turns
- parallel implementation work
- work intended for a branch, PR, or long-lived review

Do not trigger for code reading, concept explanation, small docs edits, single-file low-risk fixes, immutable research artifacts, or running existing scripts without code changes.

## Agent Rule

For one implementation task:

```text
exactly one owning Task Agent
zero child agents
zero same-task role agents after task_run_id exists
one optional Quality Agent after implementation
```

The Parent Orchestrator owns all agent starts. Task Agent and Quality Agent must never spawn or request child agents. If the scope is wrong, return `BLOCKED` with evidence; Parent closes or pauses the run and replans instead of adding role agents to the same task.

## Run Directory

Create exactly one canonical run directory:

```text
.ecc/runs/<task-run-id>/
```

Parent owns `run-state.json`, `task-brief.md`, and `decisions/`. Task Agent owns `task-agent/`, `task-handoff.md`, and `changed-files.txt`. Quality Agent owns only `quality-agent/`. Domain artifacts can stay in canonical project locations but must be referenced from `artifacts/generated-files-manifest.json`.

## State Rules

`run-state.json` is the source of truth; prose is secondary.

- `child_agents_allowed` must be false.
- `same_task_role_agents_allowed` must be false.
- `quality_agent_allowed_after_state` must be `ready_for_quality`.
- active states require `active_agent` and `active_agent_role`; non-active states must clear both.
- `quality_agent_required` is task-dependent.

Use `quality_agent_required=true` for implementation, risky workflow scripts, security-sensitive changes, PR-bound changes, or user-facing behavior. Use `false` for bootstrap records, docs-only policy updates, review-only bookkeeping, or low-risk framework setup.

## Worktree Rule

Default: do not create a worktree.

Create a worktree only for multi-file implementation, risky shared behavior, autonomous workflow changes, parallel work, long-running work, or PR-bound work. Record branch, base commit, head commit, merge base, dirty state, and final disposition in the run directory.

## Verification

Initialize and validate with the helper:

```bash
python scripts/ecc_task_run.py init \
  --run-dir .ecc/runs/<task-run-id> \
  --branch <branch> \
  --worktree <worktree> \
  --base-commit <base> \
  --head-commit <head> \
  --merge-base <merge-base> \
  --task-type <type>
```

Init defaults to `quality_agent_required=true`. Add `--no-quality-agent-required` only for allowed bootstrap, docs-only, review-only bookkeeping, or low-risk framework setup runs.

```bash
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id>
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts --require-quality-artifacts
```

Default validation checks root files, run-state invariants, manifest artifact paths/checksums/sizes/mtimes, and Quality Agent semantic compatibility whenever `quality_agent_required=true` and the run is in `passed`, `failed`, or `closed_*`.

For code or workflow script changes:

```bash
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts
python -m py_compile scripts/ecc_task_run.py
git diff --check
```

## Close-Out

Before closing, record final `head_commit`, reviewed snapshot, final disposition (`keep`, `merge`, `pr`, or `discard`), and artifact references. Never discard a worktree with uncommitted changes or unreferenced artifacts unless the decision file explicitly records approval and rationale.
