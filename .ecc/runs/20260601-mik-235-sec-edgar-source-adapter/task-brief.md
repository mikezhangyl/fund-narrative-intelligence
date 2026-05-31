# Task Brief

Implement MIK-235: SEC EDGAR submissions JSON source adapter MVP.

Scope:
- Normalize SEC EDGAR submissions metadata into source-event rows.
- Preserve CIK, ticker/company, form type, filing date, accession number, source URL, fetched_at, raw_hash, trust tier, and metadata-only evidence label.
- Add deterministic fixture tests and a live/fixture smoke CLI that writes JSON plus Chinese HTML.
- Keep this slice metadata-only: no filing text extraction, no XBRL parsing, no trading interpretation.
