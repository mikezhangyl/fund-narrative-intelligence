# Task Handoff

## Goal

Optimize the project-local ECC harness so future development sessions send only relevant context by default.

## Files Changed

- `AGENTS.md`
- `.ecc/framework-state.json`
- `.ecc/runs/20260521-token-budget-harness/`
- `docs/exec-plans/active/index.md`
- `docs/exec-plans/active/token-budget-harness.md`
- `docs/memory/current-brief.md`
- `docs/memory/architecture-decisions.index.md`
- `docs/memory/architecture-decisions.md`
- `docs/memory/operating-rules.md`
- `docs/memory/project-context.md`
- `scripts/context_brief.py`
- `skills/ecc-task-subagent-workflow/SKILL.md`
- `skills/ecc-task-subagent-workflow/references/run-contract.md`
- `skills/memory-governance/SKILL.md`
- `skills/project-bootstrap/SKILL.md`
- `tests/test_context_brief.py`

## Implementation Summary

Default harness startup now uses short context surfaces instead of full memory and historical logs. The full project memory, full ADR file, plan bodies, and run directories remain available on demand through explicit paths. A new context loader emits a bounded startup view, and the main workflow skill now uses progressive disclosure for its detailed run contract.

## Commands Run

- `python scripts/ecc_task_run.py init --run-dir .ecc/runs/20260521-token-budget-harness --branch codex/hk-market-and-sina-news --worktree main --base-commit 4d4c20fbdd4a565920a7bcd4b2b78e9eea7db10c --head-commit pending-working-tree --merge-base 4d4c20fbdd4a565920a7bcd4b2b78e9eea7db10c --task-type workflow-change --no-quality-agent-required`
- `python -m pytest tests/test_context_brief.py -q`
- `python -m ruff check scripts/context_brief.py tests/test_context_brief.py`
- `python -m py_compile scripts/context_brief.py scripts/ecc_task_run.py scripts/qa_test_run.py`
- `python scripts/context_brief.py --max-words 900`
- `wc -w AGENTS.md docs/memory/current-brief.md docs/memory/architecture-decisions.index.md docs/exec-plans/active/index.md skills/ecc-task-subagent-workflow/SKILL.md skills/project-bootstrap/SKILL.md skills/memory-governance/SKILL.md`

## Test Results

- Context loader tests passed.
- Ruff passed for the new script and tests.
- Harness helper scripts compile.
- Generated context brief is under the 900-word target.
- Default startup surface is 2,318 words versus the prior approximately 16,783-word full-memory startup surface.
- Self-review found no remaining default instruction to load full project memory, full ADR history, all plans, or all run directories.
- Canonical run validation passed with `--require-task-artifacts`.
- Follow-up self-review split framework `default_skills` from `library_skills` so workflow and memory-governance skills are not implied as default loads.
- Follow-up terminology self-check clarified that `library_skills` is project-local harness metadata, not Codex native autoload behavior, and exposed the distinction in `context_brief.py`.

## Known Risks And Assumptions

- Historical plan files remain under `docs/exec-plans/active/` for audit continuity; the curated index prevents default loading.
- Full memory files remain large by design and are now on-demand references.
- No separate Quality Agent was started; this was parent-executed with local verification and self-review.

## Suggested Quality Checks

- Validate this run with `--require-task-artifacts`.
- Re-run `python scripts/context_brief.py --max-words 900`.
- Confirm `AGENTS.md` does not instruct default loading of full memory files.
- Confirm `project-bootstrap` and `memory-governance` point to summary-first memory.
