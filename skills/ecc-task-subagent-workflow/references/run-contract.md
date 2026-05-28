# ECC Task Run Contract

Load this reference only when creating, validating, or debugging `.ecc/runs/<task-run-id>/` artifacts.

## Directory Shape

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

## Required Run State

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

Implementation lifecycle:

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

Review-only lifecycle:

```text
planned -> ready_for_quality -> quality_agent_active -> passed | failed
```

## Handoff Contract

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

## Quality Agent Contract

`quality-agent/findings.json`:

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

`quality-agent/review-state.json`:

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

Quality status must be semantically compatible with `run-state.json`: passed/closed-success states require passed Quality Agent status, mismatched `review_id` is invalid, and `fix_required_before_next_phase=true` blocks `passed` and `closed_*`.

## Manifest Contract

`artifacts/generated-files-manifest.json` records every domain or workflow artifact referenced by the run.

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

For `owned_by_task=true` local files, validation checks path existence and, when present, checksum, size, and mtime. For large directories, record exact path, commit, newest mtime, total file count, total size, and summary.

If reviewed files are not committed, use `reviewed_snapshot_type: working_tree`, set `working_tree_dirty: true`, and include per-file checksums.
