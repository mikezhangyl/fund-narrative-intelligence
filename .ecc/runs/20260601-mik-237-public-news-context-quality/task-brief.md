# Task Brief

Implement MIK-237: public news context cleanup and source-quality labels.

Scope:
- Normalize Google News RSS and Sina Finance roll rows into public-news context records.
- Label every row `context_only` and keep public news from becoming trusted facts or narrative promotion input in this slice.
- Add source-domain, source-quality label, parser-health metadata, fetched_at, provider, title, link, and published_at where available.
- Filter Sina Finance navigation/homepage/client noise and count skipped rows.
- Add fixture/live smoke CLI that writes JSON plus Chinese HTML.
