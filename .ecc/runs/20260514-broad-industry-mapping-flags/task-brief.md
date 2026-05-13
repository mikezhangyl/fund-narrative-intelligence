# Task Brief

## Goal

Flag stock-to-narrative fallback mappings that are supported only by broad holding industry terms.

## Scope

- Detect industry-only `registry_term_rule` mappings.
- Lower single broad industry-only fallback confidence from `0.52` to `0.48`.
- Add `broad_industry_fallback` precision flags and `curation_review` report output.
- Preserve `multi_match_fallback` as the higher-priority review flag.

## Acceptance

- TDD tests fail before implementation and pass after implementation.
- Pipeline output exposes broad industry precision flags in raw/scoring/report artifacts.
- Existing multi-match precision behavior remains stable.
- Full quality gates and live smoke commands pass.

## Verification

- `python -m pytest tests/test_mapping_coverage.py tests/test_cli_pipeline.py::test_pipeline_surfaces_broad_industry_precision_flags tests/test_cli_pipeline.py::test_pipeline_surfaces_multi_match_precision_flags tests/test_report_writer.py -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Notes

The live smoke outputs now expose broad industry-only fallback rows across semiconductor, healthcare, defense, new energy, baijiu, and real estate examples. The calibrated real-smoke stages remained stable after lowering single broad industry-only fallback confidence from `0.52` to `0.48`.
