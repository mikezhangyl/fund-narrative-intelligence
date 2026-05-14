# CI Quality Workflow Execution Plan

## Goal

Run the project-standard quality gates automatically in GitHub Actions.

## Scope

- Add `.github/workflows/ci.yml`.
- Install the project with the `dev` extra.
- Run Ruff, V1 acceptance, coverage tests, coverage report, and compileall.
- Add a test that keeps the CI workflow aligned with the documented quality gates.

## Non-Goals

- No deployment workflow.
- No real-provider smoke in CI yet; live data remains a local/manual smoke.
- No branch protection changes.

## Acceptance

- CI workflow contains the standard local quality commands.
- Local full quality gates pass.
