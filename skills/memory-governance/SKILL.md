---
name: memory-governance
description: Use when deciding what project knowledge to save, where to save it, how to avoid memory pollution, or how to recover context across sessions.
---

# Memory Governance

Use this skill whenever a task creates reusable knowledge.

## Buckets

- `docs/memory/current-brief.md`: short default startup memory.
- `docs/memory/architecture-decisions.index.md`: short ADR lookup surface.
- `docs/memory/project-context.md`: full durable project facts, read on demand.
- `docs/memory/architecture-decisions.md`: full decision history, read on demand.
- `.ecc/memory/project/`: reusable project memory snippets for agents.
- `.ecc/memory/global/`: cross-project framework heuristics.
- `.ecc/runs/<task-run-id>/`: task-local state, artifacts, findings, and decisions.

## Rules

- Store decisions with dates and rationale.
- Mark uncertain facts as assumptions or open questions.
- Do not store secrets, private credentials, or raw sensitive data.
- Do not duplicate large artifacts; reference paths and summaries.
- Promote run-local facts to project memory only after they are stable.
- Keep startup memory summary-first. Update `current-brief.md` only for facts that future sessions need without asking for history.
- Add or update ADR index entries when a full ADR becomes operationally relevant.
- Do not paste full historical plans or run logs into default memory.

## Close-Out Prompt

Before ending a meaningful task, answer:

```text
Project facts to keep:
Architecture decisions to record:
Run-only notes:
Global heuristics:
Do not store:
Open questions:
```
