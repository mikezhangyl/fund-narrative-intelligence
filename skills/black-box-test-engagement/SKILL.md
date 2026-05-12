---
name: black-box-test-engagement
description: Use when starting or continuing QA work for an undocumented or low-documentation system, especially when the tester has no code access and must build a living system card, manual test evidence, defects, and automation candidates before writing automated tests.
---

# Black-Box Test Engagement

Use this as the default entry skill for QA tasks in this project.

## Start

1. Read `AGENTS.md`.
2. Read `docs/testing/system-card.md`.
3. Read `.ecc/memory/project/*.md`.
4. Find the latest `.ecc/test-runs/*/run-state.json`.
5. Create a new test run when the requested goal differs from the latest run.

Initialize a run with:

```bash
python scripts/qa_test_run.py init --run-id <YYYYMMDD-purpose>
```

## Manual First

When documentation, code access, or stable test cases are missing, treat manual testing as data collection:

- map navigation and roles
- record critical flows
- capture screenshots, HAR, traces, videos, and notes
- record defects with reproduction steps
- update `docs/testing/system-card.md`
- add only stable, repeated, business-critical flows to `docs/testing/automation-candidates.md`

## Required Run Files

Each `.ecc/test-runs/<run-id>/` must contain:

```text
run-state.json
intake.md
observations/system-map.md
observations/flows.md
observations/api-observations.json
defects.md
automation-candidates.md
report.md
memory-candidates.md
evidence/index.md
```

## Phase Gates

- `manual_recon`: system map incomplete; do not automate yet.
- `manual_flow_verification`: at least one critical flow is being verified.
- `automation_candidate_selection`: stable manual flows can become smoke candidates.
- `smoke_automation`: create small Playwright smoke checks only for stable P1 flows.
- `memory_distillation`: move reusable facts to `.ecc/memory/project/` and general QA heuristics to `.ecc/memory/global-qa/`.

## Close-Out

Before ending a QA session:

```bash
python scripts/qa_test_run.py validate --run-id <run-id>
```

Then update:

- `docs/testing/system-card.md`
- `docs/testing/automation-candidates.md`
- `docs/testing/risk-register.md`
- `.ecc/memory/project/*.md`

