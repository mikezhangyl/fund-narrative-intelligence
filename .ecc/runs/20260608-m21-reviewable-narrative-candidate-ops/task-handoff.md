# Task Handoff

## Goal

Complete M21 Linear stories MIK-288 through MIK-294 after MIK-287 synchronized local `main` with `origin/main`.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

- MIK-288: hardened the Gateway source-event probe into an acceptance smoke with JSON/Chinese HTML, fixture and live modes, source-kind status classification, schema checks, owner/cache/pagination metadata, and no direct upstream calls.
- MIK-289: added source-derived candidate review queue from existing candidate inbox/digest artifacts, with filters and stable evidence links.
- MIK-290: added candidate evidence drill-down by candidate_id, preserving source_event_id and degraded/missing evidence rows.
- MIK-291: added append-only review action ledger with idempotency and Chinese summary report.
- MIK-292: added read-only trust preflight with pass/warning/fail criteria and Chinese report.
- MIK-293: added operator workflow linking daily digest to queue/evidence/preflight artifacts.
- MIK-294: added formal M21 acceptance report with artifact references, status buckets, coverage matrices, risks, and PM/Architect decision language.

## Commands Run

- `uv run pytest tests/test_narrative_source_gateway_consumer.py -q`
- `uv run pytest tests/test_source_candidate_review_queue.py -q`
- `uv run pytest tests/test_candidate_evidence_detail.py -q`
- `uv run pytest tests/test_source_review_action_ledger.py -q`
- `uv run pytest tests/test_source_trust_preflight.py -q`
- `uv run pytest tests/test_source_operator_workflow.py -q`
- `uv run pytest tests/test_m21_acceptance_report.py -q`
- `uv run pytest tests/test_m21_acceptance_report.py tests/test_source_operator_workflow.py tests/test_source_trust_preflight.py tests/test_source_review_action_ledger.py tests/test_candidate_evidence_detail.py tests/test_source_candidate_review_queue.py tests/test_narrative_source_gateway_consumer.py -q`
- `uv run pytest -q`
- `uv run ruff check .`
- `python scripts/ecc_task_run.py validate --run-dir .ecc/runs/20260608-m21-reviewable-narrative-candidate-ops`

## Test Results

- Full repository tests: `715 passed, 1 skipped in 12.04s`.
- Full ruff: passed.
- ECC run validation: passed before final run-state handoff update; rerun required after this handoff commit.

## Known Risks And Assumptions

- Gateway live responses omit explicit `owner_service`; FNI reports `stock-data-gateway` from the consumer contract and marks `owner_service_source=fni_contract_default`.
- Live trust preflight is `warning`, not `pass`, because source diversity/freshness still need stronger live evidence.
- Automatic trusted promotion remains explicitly not implemented.
- Generated `outputs/` artifacts are local and ignored by git.

## Suggested Quality Checks

- Rerun `uv run pytest -q`.
- Rerun `uv run ruff check .`.
- Review the M21 acceptance HTML: `outputs/m21_acceptance/2026-06-08-source-candidate-review/m21_acceptance_report.html`.
- Review cross-link assumptions in `source_operator_workflow` before turning the artifacts into a hosted UI.
