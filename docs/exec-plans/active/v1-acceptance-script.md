# V1 Acceptance Script Execution Plan

## Goal

Make V1 acceptance a single script that proves the pipeline runs, generated artifacts are contract-valid, mock data is visibly disclosed, and future web-loading artifacts are present.

## Scope

- Add `scripts/validate_v1_acceptance.py`.
- Generate fund `000001` outputs into a temporary or explicit output directory.
- Run the artifact contract validator.
- Check mock source URLs, data-quality disclosure, manifest, and review queue presence.
- Update documentation and project memory.

## Non-Goals

- No CI provider configuration yet.
- No web UI.
- No real-provider smoke replacement.

## Acceptance

- `python scripts/validate_v1_acceptance.py` passes.
- Tests cover passing script flow and failure on missing mock source disclosure.
- Full lint, compile, coverage, and smoke checks pass.
