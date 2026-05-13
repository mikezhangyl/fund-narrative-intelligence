# Risk Notes

## Residual Risks

- Registry-term fallback is intentionally low-confidence and keyword-based.
- Broader real-provider usefulness depends on narrative registry terms being maintained.
- Fallback mapping should not mutate the approved registry.

## Guardrails

- Exact mappings are preferred over fallback mappings.
- Fallback mappings use lower weight/confidence and method `registry_term_rule`.
- Reports expose mapping coverage and method counts.
