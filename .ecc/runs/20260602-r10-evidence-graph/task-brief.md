# R10 Evidence Graph

## Scope

Implement the narrative comparison and evidence graph slice:

- `MIK-184` Narrative comparison and evidence graph.
- `MIK-187` Evidence graph and comparison model.

## Acceptance

- Build graph nodes for narratives, source events, stocks, sectors, and concepts.
- Build only explicit evidence/entity edges with provenance and confidence.
- Compare selected narratives by shared source events, shared entities, and degraded/contradiction markers.
- Emit JSON plus canonical Chinese HTML.
- Register the generated artifact in product shell.

## Verification

- TDD tests for graph contract, unsupported inference policy, comparison metrics, CLI, HTML, and route registration.
- Full test suite, lint, diff whitespace, and ECC validation.
