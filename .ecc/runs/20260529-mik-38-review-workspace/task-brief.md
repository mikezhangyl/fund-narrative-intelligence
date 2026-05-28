# Task Brief

## Goal

Implement Linear MIK-38: provide a CLI/HTML human review workspace MVP.

## Scope

- Build a review workspace script that reads Narrative Service queue, candidate
  detail, and evidence pack endpoints.
- Render JSON and Chinese HTML grouped by review status with missing gates.
- Link candidate detail and evidence detail endpoints.
- Allow optional approve/reject/defer submission through service review-action
  endpoint before rendering.

## TDD Notes

- RED: tests failed because `scripts/run_narrative_review_workspace.py` did not
  exist.
- GREEN: added build/render/fetch/action/write workflow and verified with a
  real local Narrative Service in tests.
