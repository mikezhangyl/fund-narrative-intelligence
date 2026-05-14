# Task Brief

## Goal

Write a dedicated review queue JSON artifact for future web approval workspace loading.

## Scope

- Add `outputs/fund_<code>_review_queue.json`.
- Include metadata, fund identity, candidate review queue, candidate narratives, excluded mapping candidates, and provider foundation.
- Return the artifact path from `run_pipeline`.
- Keep raw/scoring queue fields intact.

## Acceptance

- Tests verify artifact existence and payload shape.
- Quality gates and smoke commands pass.

## Verification

- `python -m pytest tests/test_cli_pipeline.py::test_pipeline_excludes_known_bad_mapping_candidates -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`
- `ls outputs/*review_queue.json`
- `python -m json.tool outputs/fund_320007_review_queue.json`
- `python -m json.tool outputs/fund_003834_review_queue.json`

## Outcome

Pipeline now writes `fund_<code>_review_queue.json` beside raw, scoring, Markdown, and HTML artifacts. The artifact contains metadata, fund identity, provider foundation, candidate review queue, candidate narratives, and excluded mapping candidates so a future web workspace can load review work directly.
