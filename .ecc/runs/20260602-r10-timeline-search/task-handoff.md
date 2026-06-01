# Task Handoff

## Goal

Finish `MIK-183` and `MIK-186`: narrative timeline and source-event search contract.

## Files Changed

- `src/scanners/narrative_timeline_search.py`
- `scripts/run_narrative_timeline_search.py`
- `src/product_shell/route_registry.py`
- `tests/test_narrative_timeline_search.py`
- Product shell and research-workbench generated outputs.

## Implementation Summary

- Added source-event search filters and pagination.
- Added evidence/source citations per result.
- Added degraded-source semantics.
- Added JSON and Chinese HTML outputs.
- Added product shell route and artifact discovery.

## Commands Run

- `uv run pytest tests/test_narrative_timeline_search.py -q`
- `uv run pytest tests/test_narrative_timeline_search.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run python scripts/run_narrative_timeline_search.py --input outputs/narrative_source_gateway_probe/current/narrative_source_gateway_probe.json --output-dir outputs/narrative_research_workbench/current --page-size 50`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Test Results

- RED state captured for missing scanner/CLI.
- Focused tests: `24 passed`.
- Full suite: `630 passed, 1 skipped`.
- Ruff: passed.
- Whitespace diff check: passed.

## Known Risks And Assumptions

- The artifact is as fresh as the source-event probe used as input.
- Provider/source fetching remains Gateway-owned.

## Suggested Quality Checks

- Regenerate after each fresh gateway probe.
- Use query filters to inspect narrative/ticker/source-specific subsets.
