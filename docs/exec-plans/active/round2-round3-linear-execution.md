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
4. Done locally, pending Linear closeout - `MIK-55`: structured news-to-candidate narrative intake.
5. `MIK-56`: announcement-to-evidence mapping intake.
6. `MIK-65`: fund report artifact contract.
7. `MIK-57`: fund narrative change monitor report.
8. `MIK-58`: reviewable fund report pack.
9. `MIK-66`: governance audit schema and export contract.
10. `MIK-59`: narrative governance audit export.
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
