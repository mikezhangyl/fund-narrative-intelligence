---
name: memory-governance
description: Use when deciding what project knowledge to save, where to save it, how to avoid memory pollution, or how to recover context across sessions.
---

# Memory Governance

Use this skill whenever a task creates reusable knowledge.

## Buckets

- `docs/memory/`: durable human-readable project facts and decisions.
- `.ecc/memory/project/`: reusable project memory snippets for agents.
- `.ecc/memory/global/`: cross-project framework heuristics.
- `.ecc/runs/<task-run-id>/`: task-local state, artifacts, findings, and decisions.

## Rules

- Store decisions with dates and rationale.
- Mark uncertain facts as assumptions or open questions.
- Do not store secrets, private credentials, or raw sensitive data.
- Do not duplicate large artifacts; reference paths and summaries.
- Promote run-local facts to project memory only after they are stable.

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

