# Task Handoff

## Goal

Finish `MIK-184` and `MIK-187`: narrative comparison and evidence graph model.

## Files Changed

- `src/scanners/narrative_evidence_graph.py`
- `scripts/run_narrative_evidence_graph.py`
- `src/product_shell/route_registry.py`
- `tests/test_narrative_evidence_graph.py`
- Product shell and research-workbench generated outputs.

## Implementation Summary

- Built evidence graph from existing timeline/source-event artifact rows.
- Added explicit provenance-backed edges only.
- Added comparison metrics and degraded-source contradiction markers.
- Added JSON and Chinese HTML outputs.
- Added product shell route and artifact discovery.

## Commands Run

- `uv run pytest tests/test_narrative_evidence_graph.py -q`
- `uv run pytest tests/test_narrative_evidence_graph.py tests/test_narrative_timeline_search.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run python scripts/run_narrative_evidence_graph.py --input outputs/narrative_research_workbench/current/narrative_timeline_search.json --output-dir outputs/narrative_research_workbench/current --narrative 'AI infrastructure' --narrative '半导体 A股'`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Test Results

- RED state captured for missing scanner/CLI.
- Focused tests: `27 passed`.
- Full suite: `633 passed, 1 skipped`.
- Ruff: passed.
- Whitespace diff check: passed.

## Known Risks And Assumptions

- Graph freshness and coverage depend on the timeline/search input artifact.
- The implementation intentionally omits unsupported inferred edges.

## Suggested Quality Checks

- Regenerate after refreshing `narrative_timeline_search.json`.
- Compare graph output against source-event citations before using in review.
