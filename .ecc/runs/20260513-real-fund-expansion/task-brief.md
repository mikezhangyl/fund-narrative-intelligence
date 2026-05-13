# Task Brief

## Goal

Expand V1 from one live Eastmoney smoke fund to a repeatable multi-fund real-holdings smoke set.

## Scope

- Probe candidate Eastmoney fund codes and select a cross-sector smoke set.
- Add a real-fund smoke runner that writes summary JSON and Markdown.
- Ensure every selected real fund can generate the four standard artifacts.
- Broaden narrative registry and mapping fixtures enough to expose useful primary narratives and mapping coverage.
- Add tests for smoke summary shape and minimum coverage.

## Out Of Scope

- Real news, financial, valuation, or signal providers.
- LLM mapping.
- Investment advice.
- Frontend workspace.

## Required Verification

- Full pytest suite.
- Mock batch command.
- Real-fund smoke command.
- Eastmoney single-fund smoke.
