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
5. Done locally, pending Linear closeout - `MIK-56`: announcement-to-evidence mapping intake.
6. Done locally, pending Linear closeout - `MIK-65`: fund report artifact contract.
7. Done locally, pending Linear closeout - `MIK-57`: fund narrative change monitor report.
8. Done locally, pending Linear closeout - `MIK-58`: reviewable fund report pack.
9. Done locally, pending Linear closeout - `MIK-66`: governance audit schema and export contract.
10. Done locally, pending Linear closeout - `MIK-59`: narrative governance audit export.
11. `MIK-64`: durable Narrative Service storage migration path.
12. `MIK-52` + `MIK-60`: close parent packs after all child issues pass.

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

## Round 3 Queue

Execute Round 3 after Round 2 foundations, unless a Round 2 slice directly
unblocks a radar slice earlier:

1. `MIK-80` + `MIK-81` + `MIK-82`: ownership, score schema, time-series model.
2. `MIK-75`: deterministic heat and trend scoring.
3. `MIK-76`: structured source mining into candidate narrative signals.
4. `MIK-74` + `MIK-84`: radar bubble API and visualization contract.
5. `MIK-77` + `MIK-85`: evidence drill-down and review/trust integration.
6. `MIK-78`: service-owned preview surface.
7. `MIK-79`: optional AI explanation as non-authoritative evidence summary.
8. `MIK-68` + `MIK-69`: close parent packs after all child issues pass.

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
