# Task Brief

Implement V0 market-data source validation infrastructure for the stock narrative
signal project without adding trading strategy, AI prediction, browser automation,
proxy rotation, or social scraping.

Scope:

- Add a modular provider layer for Tushare and AkShare.
- Add request pacing, retry, cache, request logging, health checks, and fallback support.
- Add deterministic breadth and sector scanners.
- Add a stress-test harness for historical scans, daily updates, and sector rotation scans.
- Add lightweight storage adapters for filesystem/cache-first operation with optional
  Parquet/PostgreSQL paths.
- Keep the existing fund narrative provider layer intact.
- Pin the optional market-data AkShare dependency to the validated newer version.
