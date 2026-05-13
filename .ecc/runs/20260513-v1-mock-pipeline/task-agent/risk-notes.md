# Risk Notes

## Residual Risks

- Scoring is heuristic `scoring-v1`; it is designed for explainability and implementation validation, not financial model accuracy.
- Fixtures are mock data and should not be interpreted as real fund holdings or real evidence.
- HTML rendering is intentionally simple for V1; it is acceptable for artifact output but not a polished workspace UI.
- Coverage could not be measured because coverage tooling is not installed in the environment, though the focused tests pass.

## Guardrails Implemented

- Reports include an explicit non-investment-advice disclaimer.
- Real provider mode degrades to mock and records `provider_fallback`.
- Invalid fund codes fail with a non-zero exit code.
- Generated outputs are ignored by git.
