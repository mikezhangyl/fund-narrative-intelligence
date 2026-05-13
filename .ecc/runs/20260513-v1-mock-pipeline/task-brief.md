# Task Brief

## Goal

Implement the V1 mock-first pipeline so `python -m src.main --fund-code 000001` runs without real API credentials and produces raw JSON, scoring JSON, Markdown report, and HTML report artifacts.

## Scope

- Python CLI entrypoint.
- Local structured fixtures for fund holdings, narrative registry, evidence, and signal events.
- Mock providers and deterministic orchestration.
- Stock-to-narrative mapping, fund narrative aggregation, signal scoring, and lifecycle stage calculation.
- Markdown and HTML report generation.
- Focused tests for scoring, aggregation, CLI artifact generation, and degraded provider behavior.

## Out Of Scope

- Real AKShare, Tushare, Eastmoney, yfinance, CNINFO, exchange, crawler, or search API integration.
- LLM-dependent mapping or report generation.
- Frontend workspace.
- Investment advice, recommendations, buy/sell signals, or real-time alerts.

## Write Boundaries

- `src/`
- `tests/`
- `data/fixtures/`
- `docs/exec-plans/active/`
- `docs/memory/`
- `.ecc/runs/20260513-v1-mock-pipeline/`
- root Python project metadata when needed.

## Expected Outputs

- `outputs/fund_000001_raw.json`
- `outputs/fund_000001_scoring.json`
- `outputs/fund_000001_report.md`
- `outputs/fund_000001_report.html`

## Required Verification

- Run tests.
- Run the acceptance command.
- Inspect the generated artifacts for required metadata and report disclaimer.

## Stop Conditions

- If a real provider or credential is needed to pass acceptance, stop and re-scope because V1 must be mock-first.
- If output would imply investment advice, stop and revise report language.
