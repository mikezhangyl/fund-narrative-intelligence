# Task Brief

## Goal

Correct the new project scaffold to the intended merged ECC + Superpower + memory framework.

## Scope

- Replace QA-only default operating rules with general ECC operating mode.
- Add project bootstrap, memory governance, and finish-branch skills.
- Add execution-plan and memory docs.
- Keep QA skills as optional library skills.
- Create a canonical `.ecc/runs/` bootstrap record.

## Out Of Scope

- Product implementation.
- Git repository initialization.
- Starting sub-agents.

## Expected Outputs

- General project framework scaffold.
- Project-local rules and memory baseline.
- Recoverable framework state.

## Required Verification

- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260512-framework-bootstrap --require-task-artifacts`
- JSON syntax checks.
