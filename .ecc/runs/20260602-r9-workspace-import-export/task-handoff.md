# Task Handoff

## Goal

Finish `MIK-179` and `MIK-182`: workspace import/export package and manifest contract.

## Files Changed

- `src/product_shell/workspace_store.py`
- `scripts/manage_product_workspace.py`
- `tests/test_product_shell_workspace_store.py`
- Product shell generated outputs under `outputs/product_shell/round8-current/`

## Implementation Summary

- Added `product-shell-workspace-export-v1` JSON package.
- Added manifest fields for schema version, export id, contents, compatibility, excluded sensitive paths, and restore policy.
- Added artifact-index sanitization that excludes secret-like rows.
- Added deterministic import into a target `JsonWorkspaceRepository`.
- Added Chinese HTML export summary.

## Commands Run

- `uv run pytest tests/test_product_shell_workspace_store.py::test_workspace_export_package_excludes_sensitive_artifact_indexes -q`
- `uv run pytest tests/test_product_shell_workspace_store.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run python scripts/manage_product_workspace.py export ...`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Test Results

- RED state captured for missing export builder.
- Focused tests: `33 passed`.
- Full suite: `626 passed, 1 skipped`.
- Ruff: passed.
- Whitespace diff check: passed.

## Known Risks And Assumptions

- The package is a JSON manifest package; file archive bundling is future work.
- Import restores local workspace state only and intentionally does not restore trusted service records.

## Suggested Quality Checks

- Import `workspace_export.json` into a temporary store and inspect `workspace_state.html`.
- Confirm sensitive artifact rows are listed in `excluded_secret_paths` and absent from exported artifacts.
