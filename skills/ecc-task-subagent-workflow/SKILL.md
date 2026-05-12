---
name: ecc-task-subagent-workflow
description: Use for complex ECC implementation tasks that need a single owning Task Agent, a later Quality Agent, runtime-checkable anti-nesting rules, one canonical .ecc run directory, and scoped worktree usage. Trigger for multi-file features, cache/data-layer changes, autonomous agent workflow changes, long-running implementation, parallel implementation, or work intended for a PR. Do not trigger for reading code, explanations, small docs edits, immutable research artifact generation, or low-risk single-file fixes.
---

# ECC Task Sub-Agent Workflow

Use this skill for complex implementation tasks only. It is an execution discipline layer, not a replacement for existing domain skills.

## Default Rule

Default to parent execution. Use this workflow only when the task is large, risky, autonomous, parallel, or intended to become a branch/PR.

Trigger when at least one condition is true:

- multi-file implementation touching shared behavior
- data/cache layer changes
- autonomous agent workflow changes
- long-running feature work likely to span multiple turns
- parallel implementation work
- work intended to become a PR or long-lived branch

Do not trigger for:

- reading code
- explaining concepts
- small documentation edits
- immutable research or factor artifact generation
- running existing scripts without code changes
- single-file low-risk fixes

## Non-Nesting Rule

For one implementation task:

```text
exactly one owning Task Agent
zero child agents
zero same-task role agents after task_run_id exists
one optional Quality Agent after implementation
```

Role specialists may be used before a task run exists, during planning or scoping. Once the Parent Orchestrator creates a `task_run_id`, same-task role-agent fanout is forbidden. The only later agent type allowed for that run is the Quality Agent, and only through the documented quality transition.

The Parent Orchestrator owns all agent starts. Task Agent and Quality Agent must never spawn or request child agents. If a Task Agent finds that the task scope is wrong, it returns `BLOCKED`; the Parent closes or pauses the run and replans instead of adding a role agent to the same task.

## Run Directory

Create exactly one canonical run directory:

```text
.ecc/runs/<task-run-id>/
  run-state.json
  task-brief.md
  task-handoff.md
  changed-files.txt
  task-agent/
    implementation-notes.md
    commands.jsonl
    test-results.json
    risk-notes.md
  quality-agent/
    quality-report.md
    findings.json
    commands.jsonl
    test-results.json
    review-state.json
  artifacts/
    generated-files-manifest.json
    screenshots/
    reports/
    logs/
  decisions/
    parent-decision.md
    finish-branch-decision.md
```

Parent writes `run-state.json`, `task-brief.md`, and `decisions/`. Task Agent writes `task-agent/`, `task-handoff.md`, and `changed-files.txt`. Quality Agent writes only `quality-agent/`. Domain artifacts may remain in their canonical docs location but must be referenced from `artifacts/generated-files-manifest.json`.

## Run Artifact Retention

Commit lightweight audit records under `.ecc/runs/` when they explain a branch, commit, review, or workflow decision:

- `run-state.json`
- `task-brief.md`
- `task-handoff.md`
- `changed-files.txt`
- `task-agent/*.md`
- `task-agent/*.json`
- `task-agent/*.jsonl`
- `quality-agent/*.md`
- `quality-agent/*.json`
- `quality-agent/*.jsonl`
- `artifacts/generated-files-manifest.json`
- `decisions/*.md`

Do not commit bulky raw attachments by default. `.gitignore` excludes `.ecc/runs/**/artifacts/screenshots/` and `.ecc/runs/**/artifacts/logs/`. If a screenshot or log is needed for audit, keep it in the run directory locally and reference it from `artifacts/generated-files-manifest.json` with path, size, newest mtime, and summary. Commit a small report or summary instead of raw bulk output.

## Run State

`run-state.json` is the machine-readable source of truth. The plan or prose ledger is secondary.

Required fields:

```json
{
  "task_run_id": "task-run-id",
  "task_state": "planned",
  "review_cycle": 0,
  "branch": "codex/example",
  "worktree": ".worktrees/example",
  "base_commit": "commit",
  "head_commit": null,
  "merge_base": null,
  "quality_reviewed_commit": null,
  "reviewed_snapshot_type": null,
  "working_tree_dirty": false,
  "task_type": "implementation | review-only | workflow-change | project-bootstrap | skill-review-fix | helper-implementation | workflow-retention-policy",
  "task_agent_required": true,
  "quality_agent_required": true,
  "final_decision": null,
  "review_outcome": null,
  "owning_task_agent": null,
  "active_agent": null,
  "active_agent_role": null,
  "child_agents_allowed": false,
  "same_task_role_agents_allowed": false,
  "quality_agent_allowed_after_state": "ready_for_quality"
}
```

Allowed implementation lifecycle:

```text
planned -> task_agent_active
task_agent_active -> ready_for_quality
task_agent_active -> blocked
ready_for_quality -> quality_agent_active
quality_agent_active -> needs_task_fix
quality_agent_active -> passed
quality_agent_active -> failed
needs_task_fix -> task_agent_active
blocked -> planned
passed -> closed_keep | closed_merge | closed_pr | closed_discard
failed -> closed_keep | closed_discard
```

Allowed review-only lifecycle:

```text
planned -> ready_for_quality -> quality_agent_active -> passed | failed
```

For review-only runs, `task_agent_required` may be false and `owning_task_agent` may remain null. The Parent must set `task_state: ready_for_quality` after writing the task brief and before starting Quality Agent.

`quality_agent_required` is task-dependent:

- use `true` for implementation, risky workflow scripts, security-sensitive changes, PR-bound changes, or user-facing behavior
- use `false` for bootstrap records, docs-only policy updates, review-only bookkeeping, or low-risk framework setup
- when `quality_agent_required` is true, `passed` requires Quality Agent artifacts and `quality_reviewed_commit` or an explicit working-tree review snapshot

Active-agent invariant:

- `task_agent_active` requires `active_agent_role: implementation` and non-null `active_agent`.
- `quality_agent_active` requires `active_agent_role: quality` and non-null `active_agent`.
- Every non-active state must set `active_agent: null` and `active_agent_role: null`.

## Preflight Checks

Before starting any agent, Parent must check:

- `task_run_id` matches the canonical run directory
- `child_agents_allowed` is false for Task Agent and Quality Agent
- no same-task role agent is started after `task_run_id` exists
- no second Task Agent starts when `active_agent` is set
- Quality Agent starts only when `task_state` is `ready_for_quality`
- implementation is not reopened after `passed` unless Parent records a new `review_cycle`
- non-active states have `active_agent` and `active_agent_role` cleared

Before creating a worktree:

- verify branch/path uniqueness
- run `git worktree list` and record existing worktrees
- record `base_commit`, `head_commit`, and `merge_base`
- record whether the source workspace had unrelated uncommitted changes
- ensure `.worktrees/` is ignored if using an in-repo worktree path

Before close-out:

- record final `head_commit` and `quality_reviewed_commit`
- record final disposition as `keep`, `merge`, `pr`, or `discard`
- do not discard worktrees with uncommitted changes or unreferenced artifacts unless approval is recorded in `decisions/finish-branch-decision.md`

## Handoff

All communication is mediated by Parent and files in the run directory. Task Agent and Quality Agent do not use side-channel messages.

`task-brief.md` must include:

- task goal
- scope
- out of scope
- assigned files or write boundaries
- expected outputs
- required verification
- approval or stop conditions

`task-handoff.md` must include:

```text
# Task Handoff

## Goal
## Files Changed
## Implementation Summary
## Commands Run
## Test Results
## Known Risks And Assumptions
## Suggested Quality Checks
```

`quality-agent/findings.json` must be a JSON object:

```json
{
  "status": "passed | needs_fix | failed | blocked",
  "findings": [
    {
      "id": "F001",
      "priority": "P1",
      "file": "path",
      "lines": "1-2",
      "issue": "What is wrong.",
      "impact": "Why it matters.",
      "recommended_fix": "How to resolve."
    }
  ],
  "residual_risks": []
}
```

`quality-agent/review-state.json` must be a JSON object:

```json
{
  "review_id": "task-run-id",
  "status": "passed | needs_fix | failed | blocked",
  "reviewed_at": "YYYY-MM-DD",
  "reviewed_snapshot_type": "committed | working_tree",
  "quality_reviewed_commit": null,
  "working_tree_dirty": true,
  "findings_count": 0,
  "unresolved_findings_count": 0,
  "fix_required_before_next_phase": false
}
```

Quality Agent findings go in `quality-agent/findings.json`. If fixes are needed, Parent sets `task_state: needs_task_fix`, increments `review_cycle`, and returns findings to the same owning Task Agent. A different implementer or same-task role agent requires closing the current run and opening a new run.

## Artifact Manifest

`artifacts/generated-files-manifest.json` must record every domain or workflow artifact referenced by the run.

For files, record:

```json
{
  "type": "execution-plan",
  "path": "docs/exec-plans/active/example.md",
  "owned_by_task": true,
  "commit": "commit-or-null",
  "reviewed_snapshot_type": "committed | working_tree",
  "checksum_sha256": "sha256",
  "mtime_epoch": 0,
  "size_bytes": 0,
  "summary": "What this artifact proves."
}
```

For large directories where checksums are impractical, record exact path, commit, newest mtime, total file count, total size, and summary.

If reviewed files are not committed, do not claim `head_commit` represents the live contents. Set `reviewed_snapshot_type: working_tree`, `working_tree_dirty: true`, and include per-file checksums.

## Prompt Snippets

Task Agent:

```text
You are the owning Task Agent for <task-run-id>.
Do not spawn child agents or request same-task role agents.
Use only the canonical run directory for task artifacts.
If the task scope is wrong, return BLOCKED with reason and evidence.
```

Quality Agent:

```text
You are the Quality Agent for <task-run-id>.
Do not modify product code.
Do not spawn child agents.
Read run-state.json, task-handoff.md, changed-files.txt, and git diff.
Write findings under quality-agent/.
Return passed, needs_fix, blocked, or failed with residual risks.
```

`BLOCKED` response:

```text
BLOCKED
reason:
evidence:
recommended_next_run:
```

## Verification

Use the helper script to initialize or validate run directories:

```bash
python scripts/ecc_task_run.py init \
  --run-dir .ecc/runs/<task-run-id> \
  --branch <branch> \
  --worktree <worktree> \
  --base-commit <base> \
  --head-commit <head> \
  --merge-base <merge-base> \
  --task-type <type>

# Init defaults to quality_agent_required=true.
# Add --no-quality-agent-required only for allowed bootstrap, docs-only,
# review-only bookkeeping, or low-risk framework setup runs.
# Use --quality-agent-required when the default should be explicit.

# After initialization or before any agent starts, validate the root contract.
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id>

# After Task Agent or Parent implementation handoff, require task artifacts.
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts

# After Quality Agent review and before close-out, require both artifact sets.
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts --require-quality-artifacts
```

Default validation checks `run-state.json`, required root files, manifest artifact paths/checksums/sizes/mtimes, and Quality Agent semantic compatibility whenever `quality_agent_required=true` and the run is in `passed`, `failed`, or `closed_*`.

For docs/skill-only changes:

```bash
git diff --check
```

For code or workflow script changes:

```bash
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts
python -m py_compile scripts/ecc_task_run.py
git diff --check
```

When `quality_agent_required` is true, close-out verification must also include:

```bash
python scripts/ecc_task_run.py validate --run-dir .ecc/runs/<task-run-id> --require-task-artifacts --require-quality-artifacts
```

Phase 2 implementations must include at least one verification path proving:

- same-directory artifact colocation
- nested/fanout prevention by inspecting `run-state.json`

Concrete colocation check:

```bash
test -f .ecc/runs/<task-run-id>/task-brief.md
test -f .ecc/runs/<task-run-id>/task-handoff.md
test -f .ecc/runs/<task-run-id>/run-state.json
```

When `quality_agent_required` is true, also check:

```bash
test -f .ecc/runs/<task-run-id>/quality-agent/findings.json
test -f .ecc/runs/<task-run-id>/quality-agent/review-state.json
```

Concrete anti-fanout check:

```bash
python -m json.tool .ecc/runs/<task-run-id>/run-state.json
```

Then verify these fields:

```text
child_agents_allowed == false
same_task_role_agents_allowed == false
active_agent_role is null, implementation, or quality
non-active states have active_agent == null and active_agent_role == null
quality_agent_allowed_after_state == ready_for_quality
```
