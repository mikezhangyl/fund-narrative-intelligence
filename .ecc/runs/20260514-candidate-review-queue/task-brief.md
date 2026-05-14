# Task Brief

## Goal

Emit a workspace-ready candidate review queue for future web approval screens.

## Scope

- Add a pure review queue builder from candidate narratives and exclusions.
- Include available actions and promotion action templates.
- Wire queue into raw/scoring JSON and real-smoke summaries.
- Keep default scoring behavior unchanged.

## Acceptance

- Tests cover queue shape, empty queue behavior, pipeline output, and real-smoke summary output.
- Quality gates and smoke commands pass.

## Verification

- `python -m pytest tests/test_candidate_review_queue.py tests/test_cli_pipeline.py::test_pipeline_excludes_known_bad_mapping_candidates tests/test_real_fund_smoke.py::test_real_fund_smoke_summary_uses_runner_outputs tests/test_main_cli.py::test_main_run_real_smoke_returns_status -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Outcome

Raw/scoring JSON now emits `candidate_review_queue` with queue items, related exclusions, available actions, and approval action templates. Real-smoke summary and CLI output include queue item counts. The queue is read-ready for future web approval screens and does not persist actions or mutate scoring.
