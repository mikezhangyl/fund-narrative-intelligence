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
2. Done - `MIK-94` + `MIK-89`: Narrative Radar UI contract and service UI surface.
3. Done locally, pending Linear closeout - `MIK-97` + `MIK-92`: review/promotion state machine and complete reviewer
   workflow.
4. Done locally, pending Linear closeout - `MIK-95` + `MIK-90`: scheduling job model and operational run ledger.
5. Done locally, pending Linear closeout - `MIK-96` + `MIK-91`: durable storage migration schema and migration
   readiness.
6. Done locally, pending Linear closeout - `MIK-86` + `MIK-87`: close parent packs after all child issues pass.

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

### MIK-97 + MIK-92 - Review Workflow State Machine And Trust Promotion

- TDD red:
  targeted HTTP tests failed on missing
  `/api/v1/narratives/review-workflow/contract`,
  `/api/v1/narratives/review-workflow`, and `/narratives/review` routes.
- TDD green:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q -k 'review_workflow'`
  passed with 3 tests.
- Service endpoints:
  `GET /api/v1/narratives/review-workflow/contract`,
  `GET /api/v1/narratives/review-workflow`, and `GET /narratives/review`.
- State model:
  candidate input remains `candidate_untrusted`; queue states are
  `pending_review`, `approved_blocked_by_evidence`,
  `ready_for_trust_audit`, `rejected`, and `deferred`; successful promotion
  reports `trusted_validated`; `deprecated` is reserved for later lifecycle
  deprecation.
- Guardrail:
  review actions and preflight remain non-mutating; promotion commit is the
  only trusted-record write path; failed promotion writes no trusted records.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 48 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Product note:
  `docs/product/round4-review-workflow-state-machine-2026-05-30.html` with
  auxiliary Markdown at
  `docs/product/round4-review-workflow-state-machine-2026-05-30.md`.

### MIK-95 + MIK-90 - Operational Scheduling And Run Ledger

- TDD red:
  targeted HTTP tests failed on missing job definition/run-ledger config and
  scheduling routes.
- TDD green:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q -k 'job_schedule or manual_job_run or disabled_and_failed_jobs'`
  passed with 3 tests.
- Service endpoints:
  `GET /api/v1/narratives/jobs/contract`,
  `GET /api/v1/narratives/jobs/definitions`,
  `POST /api/v1/narratives/jobs/run`, and
  `GET /api/v1/narratives/jobs/runs`.
- Job model:
  default job definitions cover live provider smoke, source intake, radar
  scoring, and report-pack generation with enabled flags, schedules,
  parameters, timeout, concurrency guard, retry policy, and owner service.
- Run ledger:
  every manual run records `JR_*` run id, timestamps, status, duration,
  warnings, artifacts, error category, idempotency key, and
  `trusted_store_mutation=none`.
- Guardrail:
  disabled jobs fail before writing a run; unsupported job types record a
  failed run without mutating trusted registry, mapping, or evidence stores.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 51 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Product note:
  `docs/product/round4-operational-scheduling-run-ledger-2026-05-30.html`
  with auxiliary Markdown at
  `docs/product/round4-operational-scheduling-run-ledger-2026-05-30.md`.

### MIK-96 + MIK-91 - Durable Storage Migration Readiness

- TDD red:
  targeted HTTP test failed on missing
  `/api/v1/narratives/storage/migration-plan`; conformance test failed on
  missing `job_runs` ledger and Round 4 durable entity list.
- TDD green:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q -k 'storage_migration_plan'`
  and
  `uv run pytest tests/test_narrative_service_conformance_probe.py -q -k 'append_only_ledger_policy'`
  passed.
- Service endpoint:
  `GET /api/v1/narratives/storage/migration-plan`.
- Schema scope:
  migration plan covers narratives, stock mappings, evidence packs, source
  events, candidates, review actions, promotion decisions, radar source signals,
  radar snapshots, and job runs.
- Invariants:
  HTTP contracts cannot change; append-only semantics are preserved; JSON mode
  remains fallback until parity passes; trusted promotion writes remain
  `promotion_commit_only`.
- Product note:
  `docs/product/round4-durable-storage-migration-readiness-2026-05-30.html`
  with auxiliary Markdown at
  `docs/product/round4-durable-storage-migration-readiness-2026-05-30.md`.

### MIK-86 + MIK-87 - Parent Closeout

- Final lint:
  `uv run ruff check .` passed.
- Final compile:
  `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`
  passed.
- Final full suite:
  `uv run pytest -q` passed with 553 tests and 1 skipped.
- Service acceptance:
  `uv run python scripts/validate_stock_narrative_service_acceptance.py`
  completed; generated ignored artifacts under
  `outputs/stock_narrative_service_acceptance/2026-05-29T165703+0000/`.
- Diff whitespace:
  `git diff --check main...HEAD` passed.
- Product acceptance:
  `docs/product/round4-productized-narrative-operations-acceptance-2026-05-30.html`
  with auxiliary Markdown at
  `docs/product/round4-productized-narrative-operations-acceptance-2026-05-30.md`.

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
