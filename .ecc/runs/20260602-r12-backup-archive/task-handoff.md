# Task Handoff

## Goal

Complete MIK-196 and MIK-199 with backup/restore archive schema and portable local archive artifact.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds a backup restore archive builder and CLI, a default input config, generated JSON/Chinese HTML/zip artifacts, and product shell route registration. The manifest includes per-file SHA256 checksums, excluded-file reasons, compatibility metadata, restore validation requirements, and rollback support.

## Commands Run

- `uv run pytest tests/test_backup_restore_archive.py -q`
- `uv run pytest tests/test_backup_restore_archive.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run ruff check .`
- `uv run python scripts/run_backup_restore_archive.py --input config/backup_restore_archive_input.json --output-dir outputs/backup_restore_archive/current`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `651 passed, 1 skipped`.

## Known Risks And Assumptions

The archive is intentionally selected-scope rather than whole-repo. Restore overwrite is blocked unless validation succeeds.

## Suggested Quality Checks

- Inspect the zip contents before using it as an operator handoff artifact.
