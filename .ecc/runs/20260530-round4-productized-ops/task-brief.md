# Task Brief

## Goal

Complete Round 4 Productized Narrative Operations for the Fund Narrative
Intelligence project.

## Scope

- PM parent: `MIK-86`.
- Architect parent: `MIK-87`.
- PM children: `MIK-88` to `MIK-92`.
- Architect children: `MIK-93` to `MIK-97`.

## Execution Order

1. `MIK-93` + `MIK-88`: live validation taxonomy and credential-safe smoke.
2. `MIK-94` + `MIK-89`: Narrative Radar UI contract and service UI surface.
3. `MIK-97` + `MIK-92`: review/promotion state machine and reviewer workflow.
4. `MIK-95` + `MIK-90`: scheduling job model and run ledger.
5. `MIK-96` + `MIK-91`: durable storage migration schema and readiness.
6. `MIK-86` + `MIK-87`: parent closeout.

## Constraints

- TDD is mandatory.
- Do not close Linear issues before tests, documentation, and checkpoint commit
  exist.
- Do not expose secrets in live validation or smoke artifacts.
- Keep external provider access behind gateway/service contracts.
- Preserve JSON/local mode while adding migration readiness.

## Branch

`codex/round4-develop`, based on `codex/round-4-product-plan` commit
`45fa9ac9b4daf3192eda137b586624bbea975edd`.
