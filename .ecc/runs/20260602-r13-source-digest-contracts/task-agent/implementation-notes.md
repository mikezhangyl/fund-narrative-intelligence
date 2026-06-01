# Implementation Notes

- Added `src/scanners/fresh_narrative_digest.py` as a deterministic FNI-side digest builder over gateway source-event rows.
- Added `scripts/run_fresh_narrative_digest.py` to turn gateway probe/source-event JSON into JSON plus canonical Chinese HTML.
- Embedded explicit contracts for supported digest states, entity resolution, deduplication, and crawler adapter requirements.
- Updated product shell route registry so `/narratives/digest` points to the generated digest JSON/HTML.
- Regenerated the product shell outputs so the digest is discoverable through the route registry and artifact browser.

The implementation intentionally does not crawl providers directly. Live data collection stays in Gateway; this repo consumes gateway source-event artifacts.
