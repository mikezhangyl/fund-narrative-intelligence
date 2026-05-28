# Implementation Notes

## Token Reduction Strategy

The main change is summary-first context loading:

- `AGENTS.md` no longer requires full `project-context.md` and full `architecture-decisions.md` by default.
- `docs/memory/current-brief.md` is the default project memory entry point.
- `docs/memory/architecture-decisions.index.md` is the default ADR entry point.
- `docs/exec-plans/active/index.md` is now a short current queue instead of a long historical catalog.
- `scripts/context_brief.py` creates a bounded context view for new sessions.
- `ecc-task-subagent-workflow` keeps its core instructions in `SKILL.md` and moves detailed contracts into `references/run-contract.md`.

## Safety Choices

Historical plan files and `.ecc/runs/**` artifacts were not moved or deleted because existing audit records may reference those paths. The optimization is achieved by default-read policy and a curated index, not by removing history.

## Measured Result

The previously recommended startup surface was approximately 16,783 words. The new default startup surface measured by `wc -w` is 2,318 words, and the generated context brief is under 900 words.
