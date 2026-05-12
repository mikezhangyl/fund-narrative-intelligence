# Project Bootstrap Execution Plan

## Purpose

Install and use the merged ECC + Superpower + memory framework as this project's operating skeleton.

## Framework Intent

This is not a QA-only framework. It is a general project execution framework that supports development, research, testing, documentation, review, and future automation.

Merged strengths:

- ECC: local skills, explicit quality discipline, project instructions, development workflow.
- Superpower: plan-first execution, canonical work/run directories, worktree criteria, fresh review, finish-branch discipline.
- Memory system: durable project facts, decisions, run records, and reusable knowledge.

## Current Phase

`project_bootstrap`

## Initial Acceptance Criteria

- `AGENTS.md` defines the project operating mode.
- `.ecc/framework-state.json` records the active framework and phase.
- `skills/ecc-task-subagent-workflow/` is installed.
- `skills/project-bootstrap/` and `skills/memory-governance/` are installed.
- `docs/memory/` contains baseline project memory files.
- `.ecc/runs/` is available for task run records.
- QA-specific skills are optional libraries, not default mode.

## Next Steps

1. Define the product/project goal.
2. Decide whether the first implementation task needs a worktree.
3. Create the first real task run under `.ecc/runs/<task-run-id>/`.
4. Update project memory after the first meaningful decision.

