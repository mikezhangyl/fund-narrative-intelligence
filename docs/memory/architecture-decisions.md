# Architecture Decisions

## ADR-0001: Use Merged ECC Framework

- Status: accepted
- Date: 2026-05-12

Decision:

Use a project-local merged framework combining ECC workflow structure, Superpower-inspired execution discipline, and durable memory files.

Rationale:

- The project is new and needs an operating skeleton before implementation work.
- Workflows should be recoverable from files when chat context is gone.
- Agent usage should be deliberate and runtime-checkable.

Consequences:

- Complex work uses `.ecc/runs/<task-run-id>/`.
- Plans live under `docs/exec-plans/active/`.
- Durable project memory lives under `docs/memory/` and `.ecc/memory/project/`.
- QA-specific flows remain available as optional skills.

