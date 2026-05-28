# Task Brief

## Goal

Implement Linear MIK-34: expose a candidate narrative detail view for reviewers.

## Scope

- Add `GET /api/v1/narratives/candidates/{candidate_narrative_id}`.
- Return candidate metadata, trust status, review history, latest action,
  preflight gates, missing gates, recommended action, and source evidence refs.
- Return a structured `status=missing` envelope for unknown candidates without
  writing registry, mapping, evidence, intake, or review-action files.
- Add contract and conformance support for dynamic candidate detail paths.

## TDD Notes

- RED: candidate detail endpoint tests returned HTTP 404.
- RED: contract test failed because the dynamic candidate detail endpoint was
  not declared.
- GREEN: added storage read model, dynamic route, conformance path support, and
  documentation.
