# Validate Artifact Contracts CLI Execution Plan

## Goal

Expose one command that validates generated artifact contracts before future web workspace loading.

## Scope

- Add `python -m src.main --validate-artifact-contracts <path>`.
- Accept either a single manifest file or an output directory.
- Validate manifest bundles, review queue artifacts, review-action preview artifacts, and persistence-result artifacts.
- Fail when manifest-referenced files are missing or inconsistent.

## Non-Goals

- No artifact mutation.
- No web UI.
- No registry persistence changes.

## Acceptance

- Directory validation reports counts for known artifact contracts.
- Manifest-file validation verifies referenced files exist and match manifest metadata.
- Full lint, compile, coverage, and smoke checks pass.
