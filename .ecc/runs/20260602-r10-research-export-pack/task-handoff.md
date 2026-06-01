# Task Handoff

## Goal

Complete MIK-185 and MIK-188 by adding a cited research export pack and analyst-note contract to the narrative research workbench.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds a builder and CLI for `narrative_research_export_pack`, generates JSON plus Chinese HTML from existing current timeline/search and evidence graph artifacts, and registers `/research/export-pack` in the product shell. The note schema stores `linked_object_ref`, author, timestamp, body, audit metadata, and `promotion_effect=none`.

## Commands Run

- `uv run pytest tests/test_narrative_research_export_pack.py -q`
- `uv run pytest tests/test_narrative_research_export_pack.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run ruff check .`
- `uv run python scripts/run_narrative_research_export_pack.py --timeline outputs/narrative_research_workbench/current/narrative_timeline_search.json --evidence-graph outputs/narrative_research_workbench/current/narrative_evidence_graph.json --output-dir outputs/narrative_research_workbench/current`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `636 passed, 1 skipped`.

## Known Risks And Assumptions

No local analyst note artifact exists yet, so the current generated pack has `note_count=0`. The tested CLI accepts a notes JSON input and preserves notes as non-promotional user artifacts.

## Suggested Quality Checks

- Regenerate the pack when `narrative_timeline_search.json` or `narrative_evidence_graph.json` changes.
- Provide a local notes JSON with a top-level `notes` list when analysts want note content included.
- After merge, mark `MIK-185` and `MIK-188` Done. If R10 parents have no remaining open children, close `MIK-171` and `MIK-172`.
