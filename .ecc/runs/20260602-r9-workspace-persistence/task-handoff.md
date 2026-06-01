# Task Handoff

## Goal

Finish `MIK-177` and `MIK-180`: persistent local workspace state, saved views, and migration-ready repository contract.

## Files Changed

- `src/product_shell/workspace_store.py`
- `scripts/manage_product_workspace.py`
- `scripts/build_product_shell.py`
- `src/product_shell/shell.py`
- `src/product_shell/route_registry.py`
- `tests/test_product_shell_workspace_store.py`
- Product shell generated outputs under `outputs/product_shell/round8-current/`

## Implementation Summary

- Added a JSON-file workspace repository behind a `WorkspaceRepository` protocol.
- Added saved-view persistence for product shell surfaces including radar, quality, portfolio workspace, production readiness, artifact browser, source quality, and fresh digest.
- Added recursive secret-key rejection and local-only semantics.
- Added Chinese HTML output for workspace state.
- Registered `/workspace/saved-views` in the product shell.

## Commands Run

- `uv run pytest tests/test_product_shell_workspace_store.py -q`
- `uv run pytest tests/test_product_shell_workspace_store.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run python scripts/manage_product_workspace.py save-view ...`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Test Results

- RED state captured for missing workspace module and CLI.
- Focused tests: `26 passed`.
- Full suite: `619 passed, 1 skipped`.
- Ruff: passed.
- Whitespace diff check: passed.

## Known Risks And Assumptions

- JSON-file persistence is the first backend; SQLite/Postgres are contract-supported but not implemented in this slice.
- Product shell is still static HTML/JSON; interactive UI wiring can reuse the CLI/repository contract.
- Saved workspace state is local user state and cannot promote trust or alter service-owned records.

## Suggested Quality Checks

- Save another view with `scripts/manage_product_workspace.py save-view` and rebuild the product shell.
- Confirm `workspace_state.html` renders as the canonical readable artifact.
- Keep provider credentials out of saved filters; the repository rejects secret-like keys.
