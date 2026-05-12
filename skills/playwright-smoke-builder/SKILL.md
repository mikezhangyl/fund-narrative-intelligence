---
name: playwright-smoke-builder
description: Use after at least one critical manual flow is verified and stable enough to automate as a small Playwright smoke test with trace/screenshot evidence.
---

# Playwright Smoke Builder

Do not use this before manual reconnaissance has identified stable P1 flows.

## Inputs

- `docs/testing/system-card.md`
- `docs/testing/automation-candidates.md`
- current test run flow notes and evidence

## Output

- minimal smoke tests for stable P1 paths
- clear test data preconditions
- evidence-producing Playwright config when a JS project exists
- update `docs/testing/automation-candidates.md` status

Keep smoke tests small. Prefer login, navigation, and one critical happy path before broader regression.

