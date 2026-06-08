# Task Brief

## Goal

Complete M21 Linear stories in order:

MIK-288 -> MIK-289 -> MIK-290 -> MIK-291 -> MIK-292 -> MIK-293 -> MIK-294

The work starts after MIK-287 reconciled local `main` with `origin/main`.

## Scope

- Keep FNI as the consumer/reporting layer for Gateway narrative source events.
- Do not add direct SEC/CNINFO/news/social upstream calls inside FNI.
- Produce JSON plus Chinese HTML for reader-facing artifacts.
- Use TDD checkpoint slices and commit after each coherent user-story capability.

## MIK-288 Checkpoint

Implemented the live/fixture Gateway source-event acceptance smoke by hardening
`scripts/run_narrative_source_gateway_probe.py`.

Key behavior:

- Report version is now `narrative-source-gateway-acceptance-v2`.
- Each source kind receives an `acceptance_status`: `pass`, `degraded`, `no_data`,
  `missing_route`, `blocked`, or `schema_mismatch`.
- The report validates envelope, rows, source_kind, trust_tier, source_quality,
  degradation_events, pagination metadata, cache metadata, and owner_service.
- `owner_service` is reported as `stock-data-gateway`; if Gateway omits the field,
  `owner_service_source` is `fni_contract_default`.
- FNI still calls only the unified Gateway route and does not call external upstreams.

Artifacts generated locally:

- `outputs/narrative_source_gateway_probe/2026-06-08-m21-fixture/narrative_source_gateway_probe.json`
- `outputs/narrative_source_gateway_probe/2026-06-08-m21-fixture/narrative_source_gateway_probe.html`
- `outputs/narrative_source_gateway_probe/2026-06-08-m21-live/narrative_source_gateway_probe.json`
- `outputs/narrative_source_gateway_probe/2026-06-08-m21-live/narrative_source_gateway_probe.html`

Verification:

- `uv run pytest tests/test_narrative_source_gateway_consumer.py -q`: 9 passed.
- `uv run pytest tests/test_product_shell_source_quality.py tests/test_fresh_narrative_digest.py tests/test_narrative_source_coverage_gap.py -q`: 21 passed.
- `uv run ruff check scripts/run_narrative_source_gateway_probe.py src/market_data/providers/narrative_source_gateway.py tests/test_narrative_source_gateway_consumer.py`: passed.
- Fixture acceptance: 6 pass, 1 degraded, 0 blocking.
- Live acceptance against local Gateway on `127.0.0.1:8700`: 2 pass, 2 degraded, 3 no_data, 0 blocking.
