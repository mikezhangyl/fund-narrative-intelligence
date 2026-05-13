# Quality Report

## Status

Passed after reviewer fixes.

## Checks

- Focused calibration, scoring, and mock scenario tests pass.
- Full test suite passes with 44 tests.
- Coverage passes at 85% over `src`.
- Ruff lint and compile checks pass.
- V1 acceptance, mock fixture batch, and real Eastmoney smoke commands pass.

## Resolved Findings

- The `000003` mock scenario is now locked to `dead`.
- The intentional `N_AI_APPS` secondary-stage change is now covered by a regression test.

## Residual Risks

- The direct calibration test isolates deterministic scoring and does not replace the integrated real-smoke command.
- Eastmoney holdings can change independently of this repository.
- V1 signal and evidence layers remain fixture-backed for real-fund smoke reports.
