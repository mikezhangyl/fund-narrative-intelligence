# Task Handoff

## Goal

Complete MIK-189 and MIK-192 by adding a deterministic historical replay runner and versioned input/run schema.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds a replay builder, CLI, default input config, current JSON/Chinese HTML artifact, and product shell route. The run is bounded, resumable, deterministic, and explicitly scoped to system-quality evaluation.

## Commands Run

- `uv run pytest tests/test_historical_replay_runner.py -q`
- `uv run pytest tests/test_historical_replay_runner.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run ruff check .`
- `uv run python scripts/run_historical_replay.py --input config/historical_replay_input.json --output-dir outputs/historical_replay/current`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `639 passed, 1 skipped`.

## Known Risks And Assumptions

Replay input coverage depends on existing local artifacts. This runner intentionally does not fetch providers or evaluate investment outcomes.

## Suggested Quality Checks

- Regenerate after updating timeline, digest, quality, or portfolio artifacts.
- Use the generated output as input for R11 stability and alert-noise evaluation slices.
