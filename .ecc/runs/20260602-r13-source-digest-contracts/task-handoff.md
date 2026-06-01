# Task Handoff

## Goal

Finish the FNI-owned R13 source digest stories: `MIK-228`, `MIK-232`, `MIK-233`, and `MIK-234`.

## Files Changed

- `src/scanners/fresh_narrative_digest.py`
- `scripts/run_fresh_narrative_digest.py`
- `src/product_shell/route_registry.py`
- `tests/test_fresh_narrative_digest.py`
- Product shell generated artifacts under `outputs/product_shell/round8-current/`
- Digest generated artifacts under `outputs/fresh_narrative_digest/current/`

## Implementation Summary

- Added a deterministic fresh narrative digest builder over gateway source-event rows.
- Added JSON plus canonical Chinese HTML report generation.
- Added entity resolution, deduplication, candidate state, and crawler adapter contracts to the digest payload.
- Added `/narratives/digest` to the product shell route registry.
- Regenerated product shell outputs so the digest is visible in the route registry and artifact browser.

## Commands Run

- `uv run pytest tests/test_fresh_narrative_digest.py -q`
- `uv run python scripts/run_fresh_narrative_digest.py --input outputs/narrative_source_gateway_probe/current/narrative_source_gateway_probe.json --output-dir outputs/fresh_narrative_digest/current --window-start 2026-06-01T00:00:00+00:00 --window-end 2026-06-02T23:59:59+00:00`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest tests/test_fresh_narrative_digest.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Test Results

- RED pass recorded for missing digest module/CLI before implementation.
- Focused tests: `25 passed`.
- Full suite: `613 passed, 1 skipped`.
- Ruff: passed.
- Whitespace diff check: passed.

## Known Risks And Assumptions

- Freshness depends on the gateway source-event artifact supplied to the digest runner.
- Provider crawling, robots/TOS handling, and rate-limit enforcement remain Gateway-owned.
- The generated digest is an operational monitoring artifact and does not make trading claims.

## Suggested Quality Checks

- Re-run the digest CLI after each fresh gateway probe.
- Rebuild the product shell after digest regeneration when publishing artifacts.
- Confirm any new live-provider collection request lands in Gateway, then consume its source-event output from FNI.
