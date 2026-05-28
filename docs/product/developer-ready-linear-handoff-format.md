# Developer-Ready Linear Handoff Format

This format is the required shape for future Fund Narrative Intelligence Linear
issues that a developer chat should be able to pick up without rediscovering
project context.

## Required Issue Sections

Every implementation issue should include:

- Product intent: the user or architecture outcome the slice exists to create.
- Scope: the concrete files, endpoints, reports, scripts, docs, or Linear state
  that may change.
- Non-goals: adjacent work that must stay out of the slice.
- Architecture constraints: service boundaries, gateway ownership, trust rules,
  report-output policy, or linked contract docs that constrain the work.
- Dependencies: blocked-by issues, required milestones, existing commands, or
  external access assumptions.
- Acceptance criteria: observable behavior that must be true before Done.
- Verification commands: exact local commands expected before checkpointing.

## Handoff Template

Use this template for new issues:

```markdown
# User Story or Architecture Requirement

As a <role>, I want <capability>, so that <outcome>.

## Product intent

<Why this matters to the FNI roadmap or operating model.>

## Scope

<The smallest user-story-sized capability that should be implemented now.>

## Non-goals

<Explicitly exclude adjacent capabilities and future phases.>

## Architecture constraints

<Relevant service/gateway/report/trust boundaries and links.>

## Dependencies

<Blocked-by issues, prerequisite contracts, credentials, or data availability.>

## Acceptance criteria

- <Observable behavior 1>
- <Observable behavior 2>

## Verification commands

- `uv run pytest ...`
- `uv run ruff check ...`
- `uv run python -m compileall -q ...`
```

## Next-Issue Selection

A developer should pick the next highest-priority Todo issue in milestone order.
Milestone order wins before priority when a later milestone depends on earlier
foundation work. Parent epic issues should be closed only after all child issues
are Done and their implementation comments/commits are present.

## Checkpoint And Completion

After verification, every completed slice needs a checkpoint commit. If the
branch is ready for remote handoff, push the branch after the checkpoint.

The Linear completion comment should include:

- commit hash and commit title;
- implementation summary;
- tests and commands run, including red/green TDD evidence when code changed;
- artifact paths such as `.ecc/runs/<task-run-id>/`;
- residual risks or follow-up issues, if any.

## Verification Commands

Default full-release checks:

```bash
uv run pytest -q
uv run python scripts/validate_stock_narrative_service_acceptance.py
git diff --check
```

Use narrower commands for small slices, but list the exact commands in the
issue handoff and Linear completion comment.
