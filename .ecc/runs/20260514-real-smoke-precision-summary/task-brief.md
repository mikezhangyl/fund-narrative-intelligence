# Task Brief

## Goal

Aggregate mapping precision flags in real-smoke summary artifacts so registry curation work is visible in one place.

## Scope

- Add `mapping_precision_flag_count` and `mapping_precision_flags` to each fund result.
- Add a `Mapping Precision Flags` section to `real_fund_smoke_summary.md`.
- Preserve existing mapping gap and multi-mapped holding summary sections.

## Acceptance

- Tests cover summary JSON and Markdown output.
- Real smoke passes and exposes the remaining broad-industry work items.
- Full quality gates and live smoke commands pass.

## Verification

- `python -m pytest tests/test_real_fund_smoke.py -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Outcome

`outputs/real_fund_smoke_summary.md` now includes `Mapping Precision Flags`, listing the remaining broad-industry curation items: `688036` 传音控股, `688692` 达梦数据, and `600522` 中天科技.
