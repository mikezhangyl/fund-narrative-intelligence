# Task Brief

## Goal

Harden the V1 mock pipeline before real provider integration.

## Scope

- Add deterministic contract validation for loaded fixture/provider payloads.
- Add controlled pipeline errors for missing fixtures and invalid provider data.
- Improve CLI usability with optional `--list-fixtures`.
- Add tests for validation, error handling, and CLI list behavior.
- Update docs so a user can run and inspect V1 locally.

## Out Of Scope

- Real provider integrations.
- LLM calls.
- Frontend workspace.
- Financial model changes.

## Write Boundaries

- `src/`
- `tests/`
- `docs/`
- `.ecc/runs/20260513-v1-hardening/`
- root project metadata if needed.

## Required Verification

- Run the full pytest suite.
- Run the acceptance command.
- Run CLI error/list paths.
- Compile `src` and `tests`.
