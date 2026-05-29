# Round 2 / Round 3 Linear Execution Plan

Last updated: 2026-05-29

## Goal

Complete the current Fund Narrative Intelligence Linear roadmap from Round 2 and
Round 3, using TDD and marking each requirement Done only after implementation,
verification, checkpoint commit, and Linear evidence comment.

Active branch: `codex/round2-3-linear-develop`

Canonical run: `.ecc/runs/20260529-round2-round3-linear-execution/`

## Source Of Truth

- Linear project: `Fund Narrative Intelligence`
- Round 2 document: `Round 2 PM + Architect Plan`
- Round 3 document: `Round 3 Narrative Radar Service Plan`
- Local Round 3 plan: `docs/product/narrative-radar-service-plan-2026-05-29.md`
- Release baseline: `docs/product/release-baseline-2026-05-29.md`

Future implementation work starts from `main` as the accepted release baseline.

## Round 2 Queue

Execute Round 2 in dependency order:

1. Done - `MIK-61` + `MIK-53`: release baseline and merge protocol.
2. Done - `MIK-62` + `MIK-54`: live validation taxonomy and dashboard.
3. Done - `MIK-63` + `MIK-67`: source event schema and gateway change-request protocol.
4. Done - `MIK-55`: structured news-to-candidate narrative intake.
5. Done - `MIK-56`: announcement-to-evidence mapping intake.
6. Done - `MIK-65`: fund report artifact contract.
7. Done - `MIK-57`: fund narrative change monitor report.
8. Done - `MIK-58`: reviewable fund report pack.
9. Done - `MIK-66`: governance audit schema and export contract.
10. Done - `MIK-59`: narrative governance audit export.
11. Done - `MIK-64`: durable Narrative Service storage migration path.
12. Done - `MIK-52` + `MIK-60`: close parent packs after all child issues pass.

## Completed Slice Evidence

### MIK-55 - Structured News-To-Candidate Narrative Intake

- TDD red: `uv run pytest tests/test_news_candidate_intake.py -q` initially
  failed on missing `scripts.run_news_candidate_intake`.
- TDD green: `uv run pytest tests/test_news_candidate_intake.py -q` passed
  with 3 tests.
- Fixture acceptance:
  `uv run python scripts/run_news_candidate_intake.py --output-dir outputs/news_candidate_intake/2026-05-29-mik-55-fixture`
- Output JSON:
  `outputs/news_candidate_intake/2026-05-29-mik-55-fixture/news_candidate_intake_report.json`
- Output HTML:
  `outputs/news_candidate_intake/2026-05-29-mik-55-fixture/news_candidate_intake_report.html`
- Product note:
  `docs/product/structured-news-candidate-intake-2026-05-29.md`
- Verification:
  `uv run ruff check .`;
  `uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests`;
  `uv run pytest -q` (`534 passed, 1 skipped`);
  `uv run python scripts/validate_stock_narrative_service_acceptance.py`.

### MIK-56 - Announcement-To-Evidence Mapping Intake

- TDD red: `uv run pytest tests/test_announcement_mapping_intake.py -q`
  initially failed on missing `scripts.run_announcement_mapping_intake`.
- TDD green: `uv run pytest tests/test_announcement_mapping_intake.py -q`
  passed with 3 tests.
- Fixture acceptance:
  `uv run python scripts/run_announcement_mapping_intake.py --output-dir outputs/announcement_mapping_intake/2026-05-29-mik-56-fixture`
- Output JSON:
  `outputs/announcement_mapping_intake/2026-05-29-mik-56-fixture/announcement_mapping_intake_report.json`
- Output HTML:
  `outputs/announcement_mapping_intake/2026-05-29-mik-56-fixture/announcement_mapping_intake_report.html`
- Product note:
  `docs/product/announcement-mapping-intake-2026-05-29.md`
- Verification:
  `uv run pytest tests/test_announcement_mapping_intake.py tests/test_mapping_evidence_pack_report.py tests/test_source_event_schema.py -q`
  (`10 passed`);
  `uv run ruff check src/scanners/announcement_mapping_intake.py scripts/run_announcement_mapping_intake.py tests/test_announcement_mapping_intake.py`.

### MIK-65 - Fund Report Artifact Contract

- TDD red: `uv run pytest tests/test_fund_report_artifact_contract.py -q`
  initially failed on missing `run_id`, missing contract config, old missing
  artifact error shape, and missing HTML JSON artifact links.
- TDD green: `uv run pytest tests/test_fund_report_artifact_contract.py -q`
  passed with 3 tests.
- Contract config:
  `config/fund_report_artifact_contract.json`
- Product note:
  `docs/product/fund-report-artifact-contract-2026-05-29.md`
- Fixture acceptance:
  `uv run python -m src.main --fund-code 000001 --provider-mode mock --output-dir outputs/fund_report_artifact_contract/2026-05-29-mik-65-pipeline`
- Manifest validation:
  `uv run python -m src.main --validate-artifact-manifest outputs/fund_report_artifact_contract/2026-05-29-mik-65-pipeline/fund_000001_manifest.json`
- Workspace build validation:
  `uv run python -m src.main --build-workspace-snapshot outputs/fund_report_artifact_contract/2026-05-29-mik-65-pipeline`
- Verification:
  `uv run pytest tests/test_fund_report_artifact_contract.py tests/test_workspace_snapshot.py tests/test_v1_acceptance_script.py -q`
  (`24 passed`);
  `uv run pytest -q` (`540 passed, 1 skipped`).

### MIK-57 - Fund Narrative Change Monitor Report

- TDD red: `uv run pytest tests/test_fund_narrative_change_monitor.py -q`
  initially failed on missing `scripts.run_fund_narrative_change_monitor`.
- TDD green: `uv run pytest tests/test_fund_narrative_change_monitor.py -q`
  passed with 3 tests.
- Fixture acceptance:
  `uv run python scripts/run_fund_narrative_change_monitor.py --output-dir outputs/fund_narrative_change_monitor/2026-05-29-mik-57-fixture`
- Output JSON:
  `outputs/fund_narrative_change_monitor/2026-05-29-mik-57-fixture/fund_narrative_change_monitor_report.json`
- Output HTML:
  `outputs/fund_narrative_change_monitor/2026-05-29-mik-57-fixture/fund_narrative_change_monitor_report.html`
- Product note:
  `docs/product/fund-narrative-change-monitor-2026-05-29.md`
- Verification:
  `uv run pytest tests/test_fund_narrative_change_monitor.py tests/test_fund_exposure_comparison_report.py tests/test_fund_narrative_exposure_matrix_report.py -q`
  (`11 passed`);
  `uv run ruff check src/scanners/fund_narrative_change_monitor.py scripts/run_fund_narrative_change_monitor.py tests/test_fund_narrative_change_monitor.py`.

### MIK-58 - Reviewable Fund Report Pack

- TDD red: `uv run pytest tests/test_reviewable_fund_report_pack.py -q`
  initially failed on missing `scripts.run_reviewable_fund_report_pack`.
- TDD green: `uv run pytest tests/test_reviewable_fund_report_pack.py -q`
  passed with 3 tests.
- Pipeline fixture:
  `uv run python -m src.main --fund-code 000001 --provider-mode mock --output-dir outputs/reviewable_fund_report_pack/2026-05-29-mik-58-pipeline`
- Pack fixture:
  `uv run python scripts/run_reviewable_fund_report_pack.py --artifact-root outputs/reviewable_fund_report_pack/2026-05-29-mik-58-pipeline --output-dir outputs/reviewable_fund_report_pack/2026-05-29-mik-58-fixture --reference-artifact fund_holding_exposure=fund_holding_exposure_report.html --reference-artifact narrative_matrix=fund_narrative_exposure_matrix_report.html --reference-artifact mapping_evidence_pack=mapping_evidence_pack_report.html --reference-artifact change_monitor=fund_narrative_change_monitor_report.html`
- Output JSON:
  `outputs/reviewable_fund_report_pack/2026-05-29-mik-58-fixture/reviewable_fund_report_pack.json`
- Output HTML:
  `outputs/reviewable_fund_report_pack/2026-05-29-mik-58-fixture/reviewable_fund_report_pack.html`
- Product note:
  `docs/product/reviewable-fund-report-pack-2026-05-29.md`
- Verification:
  `uv run pytest tests/test_reviewable_fund_report_pack.py tests/test_fund_report_artifact_contract.py tests/test_workspace_snapshot.py -q`
  (`23 passed`);
  `uv run ruff check src/scanners/reviewable_fund_report_pack.py scripts/run_reviewable_fund_report_pack.py tests/test_reviewable_fund_report_pack.py`.

### MIK-66 - Governance Audit Schema And Export Contract

- TDD red: `uv run pytest tests/test_governance_audit_schema.py -q`
  initially failed on missing `src.scanners.governance_audit`.
- TDD green: `uv run pytest tests/test_governance_audit_schema.py -q`
  passed with 3 tests.
- Schema config:
  `config/governance_audit_schema.json`
- Product note:
  `docs/product/governance-audit-schema-2026-05-29.md`
- Fixture:
  `data/fixtures/governance_audit_records.v1.json`
- Verification:
  `uv run pytest tests/test_governance_audit_schema.py tests/test_source_event_schema.py -q`
  (`7 passed`);
  `uv run ruff check src/scanners/governance_audit.py tests/test_governance_audit_schema.py`.

### MIK-59 - Narrative Governance Audit Export

- TDD red: `uv run pytest tests/test_narrative_governance_audit_export.py -q`
  initially failed on missing `scripts.run_narrative_governance_audit_export`.
- TDD green:
  `uv run pytest tests/test_narrative_governance_audit_export.py tests/test_governance_audit_schema.py -q`
  passed with 5 tests.
- Fixture:
  `data/fixtures/narrative_governance_registry.v1.json`
- Fixture acceptance:
  `uv run python scripts/run_narrative_governance_audit_export.py --registry-path data/fixtures/narrative_governance_registry.v1.json --output-dir outputs/narrative_governance_audit/2026-05-29-mik-59-fixture`
- Output JSON:
  `outputs/narrative_governance_audit/2026-05-29-mik-59-fixture/narrative_governance_audit_export.json`
- Output HTML:
  `outputs/narrative_governance_audit/2026-05-29-mik-59-fixture/narrative_governance_audit_export.html`
- Product note:
  `docs/product/narrative-governance-audit-export-2026-05-29.md`
- Verification:
  `uv run ruff check src/scanners/governance_audit.py src/scanners/narrative_governance_audit_export.py scripts/run_narrative_governance_audit_export.py tests/test_narrative_governance_audit_export.py`.

### MIK-64 - Durable Narrative Service Storage Migration Path

- TDD red:
  `uv run pytest services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  initially failed on missing `stock_narrative_service.repository`.
- TDD green:
  `uv run pytest services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 2 tests.
- Repository contract:
  `services/stock-narrative-service/src/stock_narrative_service/repository.py`
- Product note:
  `docs/product/narrative-service-storage-migration-path-2026-05-29.md`
- Verification:
  JSON fixture repository behavior matches current `NarrativeStore`, and a
  SQLite-ready fake adapter satisfies the future repository method contract.

### MIK-52 + MIK-60 - Round 2 Parent Closeout

- PM child issues completed in Linear:
  `MIK-53`, `MIK-54`, `MIK-55`, `MIK-56`, `MIK-57`, `MIK-58`, `MIK-59`.
- Architecture child issues completed in Linear:
  `MIK-61`, `MIK-62`, `MIK-63`, `MIK-64`, `MIK-65`, `MIK-66`, `MIK-67`.
- Round 2 checkpoint range:
  `7df28b6` through `56e9d46`.
- Latest full verification:
  `uv run pytest -q` (`551 passed, 1 skipped`);
  `uv run python scripts/validate_stock_narrative_service_acceptance.py`
  (`status=completed`, `endpoint_count=13`).
- Parent Linear closeout:
  `MIK-52` and `MIK-60` are ready to mark Done after this evidence checkpoint.

## Round 3 Queue

Execute Round 3 after Round 2 foundations, unless a Round 2 slice directly
unblocks a radar slice earlier:

1. Done - `MIK-80` + `MIK-81` + `MIK-82`: ownership, score schema, time-series model.
2. Done - `MIK-75` + `MIK-83`: deterministic heat/trend scoring and market confirmation adapter boundary.
3. Done locally, pending push/Linear closeout - `MIK-76`: structured source mining into candidate narrative signals.
4. Done locally, pending push/Linear closeout - `MIK-74` + `MIK-84`: radar bubble API and visualization contract.
5. Done locally, pending push/Linear closeout - `MIK-77` + `MIK-85`: evidence drill-down and review/trust integration.
6. `MIK-78`: service-owned preview surface.
7. `MIK-79`: optional AI explanation as non-authoritative evidence summary.
8. `MIK-68` + `MIK-69`: close parent packs after all child issues pass.

## Round 3 Completed Slice Evidence

### MIK-80 + MIK-81 + MIK-82 - Radar Boundary, Score Schema, And Signal Model

- TDD red:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q`
  initially failed because `/api/v1/narratives/radar/contract` and
  `/api/v1/narratives/radar/signals` returned 404.
- TDD green:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q`
  passed with 31 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 33 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Service contract:
  `GET /api/v1/narratives/radar/contract` declares Narrative Service
  ownership, provider/consumer boundaries, score schema, response envelope, AI
  non-authority policy, and degraded-source metadata fields.
- Time-series contract:
  `GET /api/v1/narratives/radar/signals` replays seed and intake events into
  append-only radar source signals and daily window snapshots without writing a
  failed-provider negative cache.
- Product note:
  `docs/product/narrative-radar-service-boundary-and-model-2026-05-29.html`
  with auxiliary Markdown at
  `docs/product/narrative-radar-service-boundary-and-model-2026-05-29.md`.

### MIK-75 + MIK-83 - Radar Scoring And Market Confirmation Boundary

- TDD red:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py -q`
  failed on missing scoring endpoint and market confirmation config behavior.
- TDD green:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_scores_are_deterministic_and_mark_sustained_heating services/stock-narrative-service/tests/test_http_service.py::test_radar_scores_degrade_market_confirmation_without_suppressing_source_heat -q`
  passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 35 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Service endpoint:
  `GET /api/v1/narratives/radar/scores` returns deterministic
  `radar-deterministic-v0` heat, trend, acceleration, momentum, evidence
  quality, market confirmation, source attention components, and window
  metadata.
- Market confirmation boundary:
  `ServiceConfig.market_confirmation_path` supplies a mockable normalized
  contract adapter; missing confirmation produces degraded metadata without
  suppressing source-driven heat.
- Product note:
  `docs/product/narrative-radar-scoring-and-confirmation-2026-05-29.html`
  with auxiliary Markdown at
  `docs/product/narrative-radar-scoring-and-confirmation-2026-05-29.md`.

### MIK-76 - Structured Source Mining Into Candidate Narrative Signals

- TDD red:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_mining_creates_candidate_signals_from_structured_events services/stock-narrative-service/tests/test_http_service.py::test_radar_mining_excludes_reserved_social_sources_and_discloses_policy -q`
  failed because the mined-candidates endpoint did not exist.
- TDD green:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 37 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Service endpoint:
  `GET /api/v1/narratives/radar/mined-candidates` mines review-only
  candidate narratives from structured news, announcement, and manual source
  events.
- Signal integration:
  `GET /api/v1/narratives/radar/signals` now derives candidate signals from
  structured source events when explicit `candidate_narratives` are absent.
- Source policy:
  `social_future` stays excluded; browser automation, social scraping,
  proxy/anti-bot work, and market confirmation as narrative text source remain
  disabled.
- Product note:
  `docs/product/narrative-radar-structured-source-mining-2026-05-29.html`
  with auxiliary Markdown at
  `docs/product/narrative-radar-structured-source-mining-2026-05-29.md`.

### MIK-74 + MIK-84 - Radar Bubble API And Visualization Contract

- TDD red:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_bubbles_return_visualization_ready_contract_without_recalculation services/stock-narrative-service/tests/test_http_service.py::test_radar_bubbles_empty_inputs_return_structured_metadata -q`
  failed because the bubble endpoint did not exist.
- TDD green:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 39 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service/radar.py services/stock-narrative-service/src/stock_narrative_service/app.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Service endpoint:
  `GET /api/v1/narratives/radar/bubbles` emits visualization-ready bubble rows
  from service-owned scores and source signals.
- Visualization contract:
  `bubble-chart-contract-v1` maps size, x, y, color, border, marker, and
  tooltip fields without coupling to a frontend library or requiring FNI score
  recalculation.
- Degraded/empty behavior:
  empty source inputs return `RADAR_BUBBLES_EMPTY` product-data-gap metadata
  with the visualization contract still present.
- Product note:
  `docs/product/narrative-radar-bubble-api-contract-2026-05-29.html`
  with auxiliary Markdown at
  `docs/product/narrative-radar-bubble-api-contract-2026-05-29.md`.

### MIK-77 + MIK-85 - Radar Evidence Detail And Review State

- TDD red:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py::test_radar_bubbles_return_visualization_ready_contract_without_recalculation services/stock-narrative-service/tests/test_http_service.py::test_radar_evidence_detail_tracks_review_state_transitions -q`
  failed on missing bubble `detail_path` and missing radar evidence endpoint.
- TDD green:
  the same targeted command passed with 2 tests.
- Targeted regression:
  `uv run pytest services/stock-narrative-service/tests/test_http_service.py services/stock-narrative-service/tests/test_storage_repository_contract.py -q`
  passed with 40 tests.
- Static checks:
  `uv run ruff check services/stock-narrative-service/src/stock_narrative_service/radar.py services/stock-narrative-service/src/stock_narrative_service/app.py services/stock-narrative-service/src/stock_narrative_service/storage.py services/stock-narrative-service/tests/test_http_service.py`.
- Compile:
  `uv run python -m compileall -q services/stock-narrative-service/src services/stock-narrative-service/tests`.
- Service endpoint:
  `GET /api/v1/narratives/radar/evidence?narrative_id=<id>` returns source
  evidence references, representative stocks, extracted entities, score
  components, linked candidate record, trust status, and latest review state.
- Review integration:
  pending candidate, approved/reviewed, and rejected states are explicit and
  service-owned; rejected or deprecated history remains interpretable without
  becoming a current trusted signal.
- Product note:
  `docs/product/narrative-radar-evidence-review-detail-2026-05-29.html`
  with auxiliary Markdown at
  `docs/product/narrative-radar-evidence-review-detail-2026-05-29.md`.

## Duplicate / Legacy Round 3 Issues

Linear also contains early Round 3 PM issues `MIK-70` to `MIK-73`. The formal
Round 3 plan supersedes them with `MIK-74` to `MIK-85`. During Round 3 closeout,
verify whether each early issue is duplicate coverage of a completed formal
issue and close it appropriately in Linear with evidence.

## Verification Discipline

For each user-story-sized slice:

- Write or update tests first and confirm RED when feasible.
- Implement the minimal slice.
- Run targeted tests plus relevant acceptance scripts.
- Commit with conventional commit format.
- Add a concise Linear comment with commit, tests, and artifact links.
- Mark issue Done only after verification passes.

Full release gates before merge:

```bash
uv run ruff check .
uv run python -m compileall -q src tests scripts services/stock-narrative-service/src services/stock-narrative-service/tests
uv run pytest -q
uv run python scripts/validate_stock_narrative_service_acceptance.py
git diff --check main...HEAD
```
