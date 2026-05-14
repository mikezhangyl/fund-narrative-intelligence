# Validate Artifact Manifest CLI Execution Plan

## Goal

Expose a direct CLI validator for `fund_<code>_manifest.json` so future web loaders can verify artifact discovery metadata independently.

## Scope

- Add a reusable pipeline manifest validator.
- Add `python -m src.main --validate-artifact-manifest path/to/fund_000001_manifest.json`.
- Cover generated manifest validation and malformed payload rejection.
- Update project memory.

## Non-Goals

- No web UI.
- No storage backend.
- No changes to artifact path names.

## Acceptance

- Generated manifest artifacts validate from the CLI.
- Malformed manifests fail fast with a clear contract error.
- Full lint, compile, coverage, and smoke checks pass.
