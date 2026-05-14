# Pipeline Artifact Manifest Execution Plan

## Goal

Write a machine-readable manifest beside each fund run so future web views can discover generated artifacts and source-quality state without reconstructing filenames.

## Scope

- Add `fund_<code>_manifest.json`.
- Include artifact paths, formats, data quality, provider foundation, and web-readiness metadata.
- Return the manifest path from `run_pipeline`.
- Update tests and project memory.

## Non-Goals

- No web server or UI.
- No artifact upload/storage backend.
- No change to existing raw/scoring/report payloads beyond the new manifest file.

## Acceptance

- Pipeline and CLI runs write a manifest artifact.
- The manifest references raw, scoring, review queue, Markdown, and HTML artifacts.
- Full lint, compile, coverage, and smoke checks pass.
