# Implementation Notes

- Added `src/scanners/narrative_evidence_graph.py` for explicit evidence graph construction.
- Added `scripts/run_narrative_evidence_graph.py` to consume timeline/search results and emit JSON plus Chinese HTML.
- Added nodes for narratives, events, stocks, sectors, and concepts.
- Added only explicit edges from source events to narratives/entities, with provenance and confidence.
- Added comparison metrics for shared events/entities and degraded-source contradiction markers.
- Registered `/research/evidence-graph` in product shell.
