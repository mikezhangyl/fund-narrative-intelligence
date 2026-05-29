# Round 4 Productized Narrative Operations Execution Plan

Last updated: 2026-05-30

## Goal

Complete all Round 4 Productized Narrative Operations Linear requirements,
using TDD and marking each requirement Done only after implementation,
verification, checkpoint commit, and Linear evidence comment.

Active branch: `codex/round4-develop`

Canonical run: `.ecc/runs/20260530-round4-productized-ops/`

## Source Of Truth

- Linear project: `Fund Narrative Intelligence`
- Milestone: `M10 - Productized Narrative Operations`
- Linear document: `Round 4 Productized Narrative Operations Plan`
- Local plan:
  `docs/product/round-4-productized-narrative-operations-plan-2026-05-30.md`

## Queue

Execute in dependency order:

1. Done - `MIK-93` + `MIK-88`: live validation taxonomy and credential-safe smoke
   surface.
2. Done locally, pending Linear closeout - `MIK-94` + `MIK-89`: Narrative Radar UI contract and service UI surface.
3. `MIK-97` + `MIK-92`: review/promotion state machine and complete reviewer
   workflow.
4. `MIK-95` + `MIK-90`: scheduling job model and operational run ledger.
5. `MIK-96` + `MIK-91`: durable storage migration schema and migration
   readiness.
6. `MIK-86` + `MIK-87`: close parent packs after all child issues pass.

## Slice Acceptance Rules

For every slice:

- Write tests first and confirm RED when feasible.
- Implement only the current dependency slice.
- Run targeted tests plus relevant static checks.
- Add or update product documentation when behavior or contracts change.
- Commit with conventional commit format.
- Add a Linear evidence comment with commit, tests, and artifact links.
- Mark issues Done only after verification passes.

## Completed Slice Evidence

### MIK-93 + MIK-88 - Live Validation Taxonomy And Credential-Safe Smoke

- TDD red:
  `uv run pytest tests/test_live_validation_dashboard.py -q` failed on the
  missing Round 4 taxonomy, missing row-level ownership/next-action fields,
  old status names, and secret-bearing URL leakage.
- TDD green:
  `uv run pytest tests/test_live_validation_dashboard.py -q` passed with 7
  tests.
- Targeted regression:
  `uv run pytest tests/test_live_validation_dashboard.py tests/test_stock_narrative_service_acceptance.py -q`
  passed with 8 tests.
- Static checks:
  `uv run ruff check scripts/run_live_validation_dashboard.py tests/test_live_validation_dashboard.py`.
- Compile:
  `uv run python -m compileall -q scripts tests`.
- Fixture acceptance:
  `uv run python scripts/run_live_validation_dashboard.py --output-dir outputs/live_validation_dashboard/2026-05-30-mik-93-88-fixture`
  returned `completed_with_actions`, `contract_failed_count=0`, and
  `action_required_count=7`.
- Product note:
  `docs/product/round4-live-provider-credential-smoke-2026-05-30.html` with
  auxiliary Markdown at
  `docs/product/round4-live-provider-credential-smoke-2026-05-30.md`.

### MIK-94 + MIK-89 - Narrative Radar UI Contract And Service UI Surface

- TDD red:
  targeted HTTP tests failed on missing
  `/api/v1/narratives/radar/ui-contract` and `/narratives/radar` routes.
- TDD green:
  targeted UI contract and HTML route tests passed with 4 tests.
- Service endpoints:
  `GET /api/v1/narratives/radar/ui-contract` and
  `GET /narratives/radar`.
- Boundary:
  UI owns rendering, filters, interactions, and drill-down navigation; Narrative
  Service API remains score authority; UI/FNI score recalculation is forbidden.
- Browser verification:
  screenshot at
  `.ecc/runs/20260530-round4-productized-ops/artifacts/screenshots/round4-radar-ui.png`;
  accessibility snapshot at
  `.ecc/runs/20260530-round4-productized-ops/artifacts/reports/round4-radar-ui-snapshot.md`.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Product note:
  `docs/product/round4-narrative-radar-ui-surface-2026-05-30.html` with
  auxiliary Markdown at
  `docs/product/round4-narrative-radar-ui-surface-2026-05-30.md`.

## Final Acceptance Gates

```bash
uv run ruff check .
uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests
uv run pytest -q
uv run python scripts/validate_stock_narrative_service_acceptance.py
git diff --check main...HEAD
```

## Known Boundaries

- No AI prediction, trading execution, social scraping, browser automation,
  proxy rotation, or anti-bot infrastructure.
- Gateway owns external provider access and provider degradation semantics.
- Narrative Service owns radar, candidate intake, scoring, review state, trust
  promotion, and narrative lifecycle storage contracts.
- FNI consumes downstream contracts and validates/report-pack behavior; it does
  not calculate radar scores.
