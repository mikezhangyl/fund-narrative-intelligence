# Risk Notes

## Residual Risks

- Validation is hand-written standard-library validation, not JSON Schema or Pydantic. This is acceptable for V1 but may become repetitive as provider contracts grow.
- Real providers may need normalization layers before their payloads satisfy the V1 contract.
- Coverage measurement is still unavailable in the current environment.

## Guardrails Added

- Missing fixtures produce a controlled pipeline error.
- Invalid provider payloads fail before orchestration.
- CLI can list available mock fund fixtures.
