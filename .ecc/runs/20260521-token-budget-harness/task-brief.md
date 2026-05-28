# Task Brief

## Goal

Optimize the project-local ECC harness so future development turns send only the most relevant context and avoid unnecessary token spend.

## Scope

- Replace full-memory default startup with summary-first startup.
- Add concise memory and ADR indexes.
- Add a deterministic context loader.
- Curate active-plan startup index without deleting historical plan files.
- Update local skills and operating rules that govern context loading.
- Record verification and residual risks in this run directory.

## Out Of Scope

- Product runtime behavior changes.
- Moving or deleting historical `.ecc/runs/**` artifacts.
- Editing files outside this repository.
- Reverting unrelated dirty working-tree changes.

## Required Verification

- Context loader tests pass.
- Ruff passes on the new script and tests.
- Context loader emits a bounded startup brief.
- Default startup surface is materially smaller than the previous full-memory startup.
- Self-review finds no remaining obvious token-waste default surfaces.

## Stop Conditions

Stop if a proposed optimization requires deleting audit history, moving files referenced by run manifests, or modifying files outside this repository.
