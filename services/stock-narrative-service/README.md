# Stock Narrative Service

`stock-narrative-service` is a monorepo subservice for narrative registry,
stock-to-narrative mappings, evidence packs, candidate intake, review queue,
and trust audit state.

It is intentionally exposed as an HTTP service. FNI should consume it through
`NARRATIVE_SERVICE_URL`; FNI should not import service internals.

## Run

From the FNI repo root:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8800
```

Then validate from FNI:

```bash
NARRATIVE_SERVICE_URL=http://127.0.0.1:8800 \
uv run python scripts/run_narrative_service_conformance_probe.py

NARRATIVE_SERVICE_URL=http://127.0.0.1:8800 \
uv run python scripts/run_narrative_service_provider_smoke.py
```

## Scope

First slice scope:

- normalized narrative HTTP endpoints;
- local JSON-backed seed data from FNI prototype files;
- candidate-only intake;
- review queue and trust audit surfaces.

Non-goals:

- AI narrative discovery;
- social scraping;
- browser automation;
- production review UI;
- complex database architecture.
