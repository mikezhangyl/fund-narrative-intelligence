---
name: memory-distill-qa
description: Use at the end of a QA session to classify observations into global QA memory, project memory, run-only notes, or discard, without storing secrets or sensitive customer data.
---

# Memory Distill QA

Use before closing a test run.

## Buckets

- `.ecc/memory/global-qa/`: reusable QA patterns that are not project-specific.
- `.ecc/memory/project/`: stable facts about this system.
- `.ecc/memory/run/`: temporary notes for the current run.
- discard: secrets, one-off data, stale guesses, private customer content.

## Required Output

Update `.ecc/test-runs/<run-id>/memory-candidates.md` with:

```text
Project facts to keep:
Global QA patterns to keep:
Run-only notes:
Do not store:
Open questions:
```

