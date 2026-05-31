# Task Brief

Implement MIK-236: CNINFO official disclosure event classifier expansion.

Scope:
- Convert existing CNINFO announcement metadata into source-event rows.
- Add deterministic event-class rules for contract/order, investment project, capacity expansion, M&A/restructuring, regulatory inquiry/penalty, performance forecast/report, shareholder meeting/governance, financing/refinancing, litigation/arbitration, and risk warning.
- Preserve source URL, announcement date, stock code/name, title, category, fetched_at, raw_hash, source quality, trust tier, and metadata-only evidence label.
- Add fixture/live smoke CLI that writes JSON plus Chinese HTML.
- Keep this slice metadata-only: no PDF parsing, no LLM extraction, no automatic narrative promotion.
