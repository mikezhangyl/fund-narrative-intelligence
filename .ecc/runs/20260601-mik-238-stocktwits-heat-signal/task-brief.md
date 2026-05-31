# Task Brief

Implement MIK-238: Stocktwits heat-signal controlled pilot.

Scope:
- Fetch one or more explicitly configured US symbols from Stocktwits public symbol stream.
- Normalize messages into social source events with symbol, message time, body excerpt, user/message ids, source URL, fetched_at, timeout/cache/rate-limit metadata, and heat-only trust tier.
- Keep Stocktwits off by default and bounded to smoke-style configured symbols.
- Add fixture/live smoke CLI that writes JSON plus Chinese HTML.
- Never treat social messages as facts, sentiment trading signals, user profiles, or trusted evidence.
