# Review Action Audit Artifact

## Goal

Write a separate persistence-result artifact whenever a review action is
persisted, so future web approval flows have a durable audit record distinct
from the updated registry.

## Acceptance

- CLI persistence writes a default result artifact under `--output-dir`.
- The result artifact records action ID, candidate ID, registry output path,
  overwrite flags, and registry delta.
- Explicit result output paths are guarded against source/action/registry-output
  overwrite.
- Existing result artifacts are not overwritten unless explicitly allowed.
