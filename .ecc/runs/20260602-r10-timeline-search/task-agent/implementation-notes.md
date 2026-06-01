# Implementation Notes

- Added `src/scanners/narrative_timeline_search.py` for deterministic source-event timeline/search indexing.
- Added `scripts/run_narrative_timeline_search.py` to consume gateway probe artifacts and emit JSON plus Chinese HTML.
- Added filters for narrative, ticker, sector, concept, source type, freshness, and quality state.
- Added pagination, citations, and degraded-source reporting.
- Registered the route in product shell as `/research/timeline-search`.

The scanner consumes existing source-event artifacts and does not fetch providers.
