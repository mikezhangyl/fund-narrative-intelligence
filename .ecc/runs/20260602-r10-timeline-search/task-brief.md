# R10 Timeline Search

## Scope

Implement the first Narrative Research Workbench slice:

- `MIK-183` Narrative timeline and source-event search.
- `MIK-186` Timeline and search API contract.

## Acceptance

- Search existing source events by narrative, ticker, sector, concept, source type, freshness, and quality state.
- Return paginated JSON with evidence/source citations and degraded-source semantics.
- Emit canonical Chinese HTML.
- Register the generated artifact in the product shell.
- Do not access providers directly.

## Verification

- TDD tests for filters, pagination, citations, degraded sources, CLI, HTML, and route registration.
- Full test suite, lint, diff whitespace, and ECC validation.
