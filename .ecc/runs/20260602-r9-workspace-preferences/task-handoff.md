# Task Handoff

## Goal

Finish `MIK-178` and `MIK-181`: local user preferences, workflow defaults, validation, and redaction.

## Files Changed

- `src/product_shell/workspace_store.py`
- `scripts/manage_product_workspace.py`
- `tests/test_product_shell_workspace_store.py`
- Product shell generated outputs under `outputs/product_shell/round8-current/`

## Implementation Summary

- Added preferences for default surface, watchlist, date window, display density, theme, and demo/live mode.
- Added validation for option sets.
- Added recursive secret-like key redaction with persisted redaction events.
- Added CLI support for setting preferences.
- Rendered preferences in the canonical Chinese workspace state HTML.

## Commands Run

- `uv run pytest tests/test_product_shell_workspace_store.py::test_update_workspace_preferences_sets_defaults_and_redacts_secret_keys -q`
- `uv run pytest tests/test_product_shell_workspace_store.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run python scripts/manage_product_workspace.py set-preferences ...`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Test Results

- RED state captured for missing preference updater.
- Focused tests: `29 passed`.
- Full suite: `622 passed, 1 skipped`.
- Ruff: passed.
- Whitespace diff check: passed.

## Known Risks And Assumptions

- Preference redaction is key-based in this slice.
- Preferences are local product-shell state, not trusted market data and not portfolio truth.

## Suggested Quality Checks

- Try `scripts/manage_product_workspace.py set-preferences` with a secret-like key and confirm the key is dropped.
- Rebuild product shell and verify `workspace_state.html` contains preferences but no raw secret values.
