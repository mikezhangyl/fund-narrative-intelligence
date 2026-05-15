# Artifact Optional Payload Consistency

## Goal

Make offline artifact-contract validation reject raw/scoring drift for optional
provider payloads.

## Scope

- Compare duplicated optional payloads across raw and scoring artifacts.
- Fail before workspace snapshot building when optional payloads drift.

## Non-Goals

- No provider changes.
- No report or scoring changes.

## Acceptance

- Tests fail first for raw/scoring optional payload drift.
- `_validate_artifact_contracts` rejects the drift.
- Standard quality gates pass, then the slice is merged and pushed.
