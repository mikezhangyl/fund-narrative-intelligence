# Implementation Notes

## Summary

Calibrated V1 fixture-backed real-fund smoke scoring so the fixed Eastmoney smoke set produces differentiated lifecycle stages.

## Changes

- Added an explicit real-fund calibration regression test for the six smoke narratives.
- Preserved the mock-provider baseline by tightening the `000003` expectation to `dead`.
- Added a reviewed secondary-stage regression for `N_AI_APPS` because the broader strengthening rule intentionally affects that secondary narrative.
- Added one semiconductor momentum signal fixture to support the intended `strengthening` smoke outcome.
- Broadened deterministic stage selection with a moderate-strength `strengthening` path and weaker-support `weakening` paths.
- Updated README, implementation spec, active plans, project memory, and ADRs with the calibrated real-smoke distribution.

## Reviewer Fixes

- Reviewer flagged the loose `000003` mock baseline assertion. Fixed by requiring `dead`.
- Reviewer flagged the unrecorded `N_AI_APPS` secondary-stage change. Fixed by adding an explicit regression test.

## Result

The fixed real smoke set now produces three stage families: semiconductor and defense are `strengthening`, baijiu and healthcare are `diverging`, and new energy and real estate are `weakening`.
