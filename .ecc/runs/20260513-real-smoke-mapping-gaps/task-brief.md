# Task Brief

## Goal

Expose concrete unmapped real-fund holdings in the Eastmoney smoke summary so the next registry and mapping broadening pass is driven by evidence.

## Acceptance

- Real smoke summary JSON includes `unmapped_holdings` with stock code, stock name, industry, and weight.
- Real smoke Markdown includes a `Mapping Gaps` section when any fund has unmapped holdings.
- Existing per-fund failure isolation and pass/fail behavior remain unchanged.
- Quality gates and live real smoke pass before merge.
