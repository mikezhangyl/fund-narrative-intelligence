# Provider Boundary Validation

## Goal

Validate optional provider payloads at the orchestration boundary even when
providers are injected by tests or future adapters.

## Scope

- Validate market quote payloads returned to orchestration.
- Validate valuation snapshot payloads returned to orchestration.
- Validate financial metrics payloads returned to orchestration.
- Validate news evidence payloads returned to orchestration.

## Non-Goals

- No provider implementation changes.
- No scoring changes.
- No frontend UI.

## Acceptance

- Tests fail first for malformed injected optional provider payloads.
- Orchestration rejects malformed optional payloads with `ProviderContractError`.
- Standard quality gates pass, then the slice is merged and pushed.
