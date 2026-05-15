# Artifact Optional Payload Validation

## Goal

Extend offline artifact-contract validation to all optional provider payloads
that can appear in raw and scoring JSON.

## Scope

- Validate `announcements`.
- Validate `announcement_evidence`.
- Validate `market_quotes`.
- Validate `valuation_snapshots`.
- Preserve existing `news_evidence` and `financial_metrics` validation.

## Non-Goals

- No provider changes.
- No report or scoring changes.

## Acceptance

- Artifact contract tests fail first for malformed optional payloads.
- `_validate_artifact_contracts` rejects malformed optional payloads in raw and
  scoring artifacts.
- Standard quality gates pass, then the slice is merged and pushed.
