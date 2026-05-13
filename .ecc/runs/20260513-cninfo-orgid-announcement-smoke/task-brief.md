# Task Brief

## Goal

Fix CNINFO announcement search so real Shanghai/Shenzhen A-share queries return announcement metadata, then add a repeatable live smoke command for the optional announcement-evidence path.

## Acceptance

- CNINFO payload tests cover `code,orgId` selectors.
- Announcement evidence smoke tests cover pass/fail/fetch-error behavior.
- `python -m src.main --run-announcement-smoke` returns non-zero if CNINFO metadata, evidence conversion, announcement layer provenance, or mixed/mock disclosure is missing.
- Quality gates and live smoke pass before merge.
