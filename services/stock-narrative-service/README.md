# Stock Narrative Service

`stock-narrative-service` is a monorepo subservice for narrative registry,
stock-to-narrative mappings, evidence packs, candidate intake, review queue,
review action ledger, promotion preflight, and trust audit state.

It is intentionally exposed as an HTTP service. FNI should consume it through
`NARRATIVE_SERVICE_URL`; FNI should not import service internals.

Runbook:

- `docs/product/stock-narrative-service-runbook.md`

## Run

From the FNI repo root:

```bash
uv run python scripts/run_stock_narrative_service.py --port 8800
```

Then validate from FNI:

```bash
uv run python scripts/validate_stock_narrative_service_acceptance.py

NARRATIVE_SERVICE_URL=http://127.0.0.1:8800 \
uv run python scripts/run_narrative_service_conformance_probe.py

NARRATIVE_SERVICE_URL=http://127.0.0.1:8800 \
uv run python scripts/run_narrative_service_provider_smoke.py
```

## Scope

First slice scope:

- normalized narrative HTTP endpoints;
- lightweight `/api/health`;
- local JSON-backed seed data from FNI prototype files;
- candidate-only intake;
- stateful review queue with optional status filtering;
- review action ledger, promotion preflight, ops summary, and trust audit
  surfaces.

Non-goals:

- AI narrative discovery;
- social scraping;
- browser automation;
- production review UI;
- automatic trusted promotion from review actions;
- automatic trusted promotion from preflight;
- complex database architecture.
