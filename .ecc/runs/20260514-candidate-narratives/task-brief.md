# Task Brief

## Goal

Add review-only candidate narratives for excluded fallback mapping candidates without changing active narrative scoring.

## Scope

- Populate candidate narratives for current Semiconductor Capex exclusions.
- Validate candidate narrative registry shape.
- Emit in-scope candidate narratives in raw/scoring JSON.
- Render candidate narratives in reports and real-smoke summaries.
- Print candidate narrative counts in `--run-real-smoke` stdout.

## Acceptance

- Candidate narratives are visible and review-ready.
- Candidate narratives do not enter `stock_narrative_mappings`, aggregation, or scoring.
- Tests cover provider, pipeline, report, real-smoke summary, and CLI behavior.

## Verification

- `python -m pytest tests/test_intelligence_providers.py::test_mock_intelligence_provider_set_loads_validated_fixture_layers tests/test_cli_pipeline.py::test_pipeline_excludes_known_bad_mapping_candidates tests/test_report_writer.py::test_html_report_renders_structured_sections_without_raw_markdown tests/test_real_fund_smoke.py::test_real_fund_smoke_summary_uses_runner_outputs tests/test_main_cli.py::test_main_run_real_smoke_returns_status -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`88%`)
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`
- `rg -n "Candidate Narratives For Review|Consumer Electronics Globalization|Domestic Database Infrastructure|Communication And Power Infrastructure|candidate_narrative_count" outputs/real_fund_smoke_summary.md outputs/real_fund_smoke_summary.json outputs/fund_320007_report.md outputs/fund_320007_report.html outputs/fund_003834_report.md outputs/fund_003834_report.html`

## Outcome

Candidate narratives are now review-only registry objects. Current excluded Semiconductor Capex candidates surface as Consumer Electronics Globalization, Domestic Database Infrastructure, and Communication And Power Infrastructure in raw/scoring JSON, reports, real-smoke summaries, and real-smoke CLI counts. They remain outside active stock mapping, aggregation, scoring, and lifecycle-stage selection.
