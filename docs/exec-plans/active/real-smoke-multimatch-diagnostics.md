# Real Smoke Multi-Match Diagnostics Execution Plan

## Purpose

Expose holdings that map to multiple narratives in the real-fund smoke summary.

## Scope

- Read raw selected stock-narrative mappings from each smoke run.
- Add `multi_mapped_holdings` to summary JSON.
- Add a Markdown `Multi-Mapped Holdings` section when applicable.
- Preserve failure isolation and existing coverage checks.

## Acceptance

- Unit tests cover multi-match JSON and Markdown output.
- `python -m src.main --run-real-smoke` passes.
- Full quality gates pass.

## Status

Implemented and locally verified.

Latest diagnostics:

- `001475`: `300604` 长川科技 maps to Semiconductor Capex Cycle and Defense Aerospace.
- `001475`: `600482` 中国动力 maps to New Energy Equipment and Defense Aerospace.

## Run Record

- `.ecc/runs/20260513-real-smoke-multimatch-diagnostics/`
