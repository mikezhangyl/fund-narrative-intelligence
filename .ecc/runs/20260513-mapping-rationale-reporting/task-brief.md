# Task Brief

## Goal

Expose why each selected stock-to-narrative mapping exists, answering the user question: "how do we know one stock belongs to a narrative?"

## Scope

- Add `mapping_rationales` to the mapping result.
- Pass rationales through raw and scoring JSON.
- Render rationales in Markdown and HTML reports.
- Document the output contract and rationale in project docs and memory.

## Acceptance

- TDD tests fail before implementation and pass after implementation.
- Full Python quality gates pass.
- Real smoke and announcement smoke still pass.

## Verification

- `python -m pytest tests/test_mapping_coverage.py tests/test_cli_pipeline.py::test_pipeline_surfaces_multi_match_precision_flags tests/test_report_writer.py -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Notes

The live `001475` report now shows why `300604` 长川科技 maps to both Semiconductor Capex Cycle and Defense Aerospace: the former is an industry-term fallback on `电子`, while the latter is a stock-name term fallback on `长川科技`; both retain `needs_review`.
