# Task Brief

## Goal

Extend V1 mock coverage beyond a single sample fund by adding multiple scenario fixtures and a batch command.

## Scope

- Add at least two more mock fund fixtures.
- Ensure scenario funds exercise different primary narrative stages.
- Add `--run-all-fixtures` CLI support.
- Add tests for fixture discovery, batch artifacts, and scenario diversity.
- Update docs and run records.

## Out Of Scope

- Real provider integration.
- LLM integration.
- Scoring model overhaul.
- Frontend workspace.

## Required Verification

- Full pytest suite.
- Batch command generates artifacts for all mock fund fixtures.
- Acceptance command for `000001` remains compatible.
