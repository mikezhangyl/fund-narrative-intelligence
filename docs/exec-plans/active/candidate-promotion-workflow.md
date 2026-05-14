# Candidate Promotion Workflow Execution Plan

## Purpose

Prepare the non-UI backend contract for future web-based candidate narrative approval.

## Scope

- Add a pure function that applies candidate review actions immutably.
- Support `approve`, `reject`, and `defer` review actions.
- Require explicit promotion metadata before approved candidates become active narratives.
- Preserve audit fields needed by a future web review workspace.
- Keep the function separate from default report generation.

## Non-Goals

- Building the web UI.
- Automatically approving candidates based on scoring output.
- Wiring promotion into the default fund report pipeline.

## Acceptance

- Tests prove approved candidates can be promoted only through explicit action.
- Tests prove rejected/deferred candidates stay outside the active registry.
- Tests prove inputs are not mutated.
- Tests prove approval requires promotion metadata and rejects duplicate active narrative IDs.

## Run Record

- `.ecc/runs/20260514-candidate-promotion-workflow/`
