# Finish Branch Decision

Task run: `20260602-fni-narrative-source-boundary-cleanup`

Decision: `merge`

Branch: `codex/fni-narrative-source-boundary-cleanup`

Reviewed commit: `b9ec2a4749500126599b083177c6511456f47e89`

Target branch: `main`

Rationale:

- The branch removes FNI-owned direct narrative source acquisition pilots that now belong in `stock-data-gateway`.
- FNI keeps only the gateway consumer/probe contract and consumer-side boundary tests.
- Verification passed before merge:
  - `uv run pytest`: `597 passed, 1 skipped`
  - `uv run ruff check .`
  - `git diff --check`
  - `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260602-fni-narrative-source-boundary-cleanup --require-task-artifacts`

Disposition:

- Merge into `main`.
- No separate worktree remains.
