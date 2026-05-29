# Round 5 Evidence Intelligence & Narrative Quality

## Linear Scope

Milestone: M11 - Evidence Intelligence & Narrative Quality

Parents:

- MIK-129 - PM requirement pack for evidence intelligence and narrative quality.
- MIK-130 - Architecture requirement pack for evidence intelligence and narrative quality.

Implementation issues:

- MIK-139 / MIK-140: evidence quality schema, deterministic scoring, source lineage, and provider reliability model.
- MIK-135 / MIK-136: evidence scorecard and structured event extraction quality review.
- MIK-141 / MIK-137: contradiction and stale narrative model plus detection output.
- MIK-142 / MIK-138: narrative quality audit API, audit export, and operator-readable workspace.

## Product Boundary

Narrative Service owns source-event normalization, quality scoring, staleness/contradiction metadata, audit APIs, and exports. FNI can consume the metadata later but must not recompute quality. This round does not introduce prediction, automatic trusted promotion, browser scraping, or AI-authoritative evidence.

## TDD Slices

1. Add failing service tests for source lineage, reliability, and evidence quality scorecards.
2. Implement deterministic quality scoring and expose `/api/v1/narratives/quality/contract`, `/api/v1/narratives/quality/scorecards`, and extraction review output.
3. Add failing tests for stale and contradictory fixtures.
4. Implement staleness/contradiction metadata and quality impact rules.
5. Add failing tests for audit API, Chinese HTML workspace, and deterministic export artifact.
6. Implement `/api/v1/narratives/quality/audit`, `/narratives/quality`, and `scripts/run_narrative_quality_audit.py`.
7. Run full local verification, create acceptance artifacts, update Linear, and close M11 issues.

## Verification

- Targeted service tests during RED/GREEN.
- `uv run ruff check .`
- `uv run python -m compileall src services scripts tests`
- `uv run pytest -q`
- `uv run python scripts/validate_stock_narrative_service_acceptance.py`
- `uv run python scripts/run_narrative_quality_audit.py --output-dir outputs/narrative_quality/round5_acceptance`
