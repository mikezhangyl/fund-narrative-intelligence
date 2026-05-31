# Task Brief

## Objective

Implement the adjusted Round 8 priority: finish `MIK-165` and `MIK-166` first
with concrete route registry and artifact index outputs, then complete
`MIK-161` and `MIK-162` with a local product home and artifact browser.

## Linear Scope

- `MIK-165`: Product shell route and data-source contract.
- `MIK-166`: Artifact index and manifest contract.
- `MIK-161`: Integrated local product shell navigation.
- `MIK-162`: Artifact browser and run history.

## Boundaries

- Product shell consumes APIs and generated artifacts only.
- Provider access, radar scoring, quality scoring, and portfolio aggregation
  remain outside shell code.
- Generated HTML remains the canonical reader-facing surface for this slice.

## Verification Gate

- Targeted product shell tests.
- Ruff, compileall, full pytest.
- Product shell CLI generation.
- ECC run validation.
