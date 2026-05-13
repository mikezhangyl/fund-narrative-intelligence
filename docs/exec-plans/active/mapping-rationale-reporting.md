# Mapping Rationale Reporting Execution Plan

## Purpose

Make stock-to-narrative mapping explainable in V1 outputs, so each mapped holding shows why it was assigned to a narrative.

## Scope

- Emit `mapping_rationales` from the mapping module.
- Include the rationale list in raw and scoring JSON.
- Render a `Mapping Rationales` section in Markdown and HTML reports.
- Keep multi-match fallback `needs_review` and `precision_flag` visible in each rationale.

## Non-Goals

- Changing the scoring formula.
- Automatically deleting broad fallback mappings.
- Adding LLM-based narrative discovery.
- Creating a manual-review UI.

## Acceptance

- Unit tests cover fixture-rule, single fallback, multi-match fallback, and unmapped rationale behavior.
- Pipeline tests cover raw/scoring/report output.
- Report writer tests cover structured HTML rationale rendering.
- Full quality gates and live smoke commands pass.

## Run Record

- `.ecc/runs/20260513-mapping-rationale-reporting/`
