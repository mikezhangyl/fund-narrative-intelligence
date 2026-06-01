# Implementation Notes

- Added `src/scanners/narrative_research_export_pack.py` to normalize timeline source events, sanitize analyst notes, build citations, and expose an export manifest.
- Added `scripts/run_narrative_research_export_pack.py` to generate JSON and Chinese HTML from existing local workbench artifacts.
- Registered `/research/export-pack` in the product shell route registry and regenerated current product shell artifacts.
- Generated current export pack from 12 real source events and 12 citations. Current note count is 0 because no local analyst note artifact was provided.
