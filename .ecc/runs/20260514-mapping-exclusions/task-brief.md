# Task Brief

## Goal

Add explicit mapping exclusions so known-bad fallback candidates do not enter narrative aggregation or scoring.

## Scope

- Add `mapping_exclusions.json` fixture.
- Load exclusions through mock/eastmoney provider paths.
- Apply exclusions to fallback candidates only.
- Emit `excluded_mapping_candidates` in raw/scoring JSON, Markdown/HTML reports, and real-smoke summaries.
- Print excluded candidate counts in `--run-real-smoke` stdout.

## Acceptance

- Tests cover mapping, provider, pipeline, report, real-smoke summary, and CLI output.
- Real smoke still passes with excluded candidates visible.
- Full quality gates and announcement smoke pass.

## Verification

- `python -m pytest tests/test_mapping_coverage.py::test_excluded_fallback_candidate_is_not_mapped_or_scored tests/test_intelligence_providers.py::test_mock_intelligence_provider_set_loads_validated_fixture_layers tests/test_cli_pipeline.py::test_pipeline_excludes_known_bad_mapping_candidates tests/test_report_writer.py::test_html_report_renders_structured_sections_without_raw_markdown tests/test_real_fund_smoke.py::test_real_fund_smoke_summary_uses_runner_outputs tests/test_main_cli.py::test_main_run_real_smoke_returns_status -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Outcome

Known-bad Semiconductor Capex fallback candidates for `688036` 传音控股, `688692` 达梦数据, and `600522` 中天科技 are excluded from scoring and aggregation. Real smoke still passes; Semiconductor coverage is now 88% and New Energy coverage is 92% because excluded candidates are intentionally unmapped.
