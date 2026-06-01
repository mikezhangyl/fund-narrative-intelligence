# Finish Branch Decision

## Decision

Merge `codex/r13-source-digest-contracts` into `main`.

## Final Snapshot

- Base commit: `76a74df0b29a3066be13af076bab4bc527768c82`
- Reviewed commit: `6754983375bdc118b8b86f13d9135df7fe78a281`
- Review outcome: passed
- Working tree before merge: clean after close-out commit

## Rationale

The branch implements the current FNI-owned R13 source digest user stories, includes deterministic tests, emits JSON plus canonical Chinese HTML, and keeps live provider crawling outside this repo.

## Verification

- `uv run pytest tests/test_fresh_narrative_digest.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260602-r13-source-digest-contracts --require-task-artifacts --require-quality-artifacts`
