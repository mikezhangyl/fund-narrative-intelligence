# V1 Mock Pipeline Execution Plan

## Purpose

Implement the first executable vertical slice for Fund Narrative Intelligence.

Acceptance command:

```bash
python -m src.main --fund-code 000001
```

Expected artifacts:

- `outputs/fund_000001_raw.json`
- `outputs/fund_000001_scoring.json`
- `outputs/fund_000001_report.md`
- `outputs/fund_000001_report.html`

## Scope

- Python CLI.
- Mock providers and local fixtures.
- Narrative registry loading.
- Stock-to-narrative mapping.
- Fund narrative aggregation.
- Signal event decay and five-dimension scoring.
- Lifecycle stage selection.
- Markdown and HTML reports with non-investment-advice disclaimer.
- Tests covering scoring, aggregation, degraded provider fallback, and CLI artifacts.

## Out Of Scope

- Real financial data providers.
- LLM calls.
- Frontend workspace.
- Historical replay engine.
- Alerts.
- Buy/sell signal generation.

## Implementation Phases

1. Create tests for scoring and aggregation behavior.
2. Create CLI integration test for required artifact outputs.
3. Implement domain models and fixture providers.
4. Implement orchestration, scoring, snapshot writing, and reports.
5. Run verification and update ECC run artifacts.

## Run Record

- `.ecc/runs/20260513-v1-mock-pipeline/`

## Status

Implemented and locally verified.

Verified commands:

- `python -m pytest -q`
- `python -m src.main --fund-code 000001`
- `python -m src.main --fund-code 000001 --provider-mode real --output-dir <tmpdir>`
- `python -m src.main --fund-code ABC`
- `python -m compileall -q src tests`

Generated outputs are ignored by git and can be regenerated from the acceptance command.
