# Risk Notes

## Residual Risks

- Scenario fixtures are deterministic mock data, not market truth.
- Stage expectations are tied to current heuristic scoring rules.
- Adding more narratives will eventually require a fixture generation or schema validation workflow.

## Guardrails

- Batch command exercises every available fund fixture.
- Scenario tests assert diverse lifecycle stages.
- Reports still include the non-investment-advice disclaimer.
