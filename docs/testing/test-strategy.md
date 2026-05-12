# Test Strategy

## Current Mode

Manual reconnaissance first, then progressive automation.

## Phase 1: Manual Recon

- Map entry URLs, login behavior, roles, modules, forms, tables, and critical flows.
- Capture screenshots, traces, HAR files, and notes under `.ecc/test-runs/<run-id>/`.
- Update `docs/testing/system-card.md` after every meaningful discovery.

## Phase 2: Manual Flow Verification

- Verify 1-3 critical flows end to end.
- Record preconditions, test data, expected results, actual results, and evidence.
- Mark stable paths as automation candidates.

## Phase 3: Smoke Automation

- Automate only stable P1 paths.
- Keep smoke tests small, deterministic, and evidence-producing.

## Phase 4: API Observation

- Infer API contracts from browser network traces.
- Mark contracts as `observed`, `inferred`, or `verified`.

## Phase 5: Regression Readiness

- Promote stable smoke tests into regression candidates.
- Add coverage map, defect evidence index, and memory distillation gate.

