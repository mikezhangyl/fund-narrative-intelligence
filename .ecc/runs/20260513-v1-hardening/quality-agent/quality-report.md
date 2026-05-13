# Quality Report

## Status

Passed with residual risks.

## Checks

- Full test suite passes.
- Acceptance command still generates all four artifacts.
- CLI lists fixtures.
- Missing fund fixture returns controlled error.
- Real provider mode records fallback.
- JSON artifacts validate with `jq`.
- Reports retain non-investment-advice language.

## Findings

No blocking findings.

## Residual Risks

- Numeric test coverage was not measured because coverage tooling is unavailable.
- Validation may need to move to schema tooling when real providers are added.
