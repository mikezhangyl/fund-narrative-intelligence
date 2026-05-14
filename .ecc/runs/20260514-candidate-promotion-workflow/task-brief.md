# Task Brief

## Goal

Define a backend-safe candidate narrative review workflow that future web approval screens can call without promoting candidates automatically.

## Scope

- Add immutable review-action application for candidate narratives.
- Support approve, reject, and defer actions.
- Promote approved candidates into active registry narratives only when an explicit approval action supplies promotion metadata.
- Preserve candidate review state and audit fields for future web UI.
- Keep default pipeline behavior unchanged.

## Acceptance

- Tests cover approval, rejection, deferral, validation errors, and immutability.
- Candidate promotion does not happen unless an explicit review action is applied.
- Quality gates pass.

## Verification

- `python -m pytest tests/test_candidate_promotion.py -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Outcome

Candidate promotion workflow now supports immutable `approve`, `reject`, and `defer` review actions. Approval requires explicit promotion metadata and appends one active narrative; reject/defer update candidate review state only. The default report pipeline remains unchanged and does not promote candidates automatically.
