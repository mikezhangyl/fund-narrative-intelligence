# Registry Rule Mapping Mode

## Goal

Add an optional stock-to-narrative mapping mode that derives mappings at runtime
from current holdings and Narrative Registry terms instead of relying on the
static `stock_narrative_mappings.json` fixture.

## Scope

- Keep the default mapping behavior unchanged.
- Add `--stock-mapping-mode registry-rule` for single pipeline runs.
- Emit the chosen mapping mode in raw and scoring artifacts.
- Mark the `Stock Mappings` provider-foundation layer as a runtime
  `registry-rule-stock-mapping` layer in registry-rule mode.
- Continue disclosing that the Narrative Registry itself remains mock-backed.

## Non-Goals

- Do not replace the Narrative Registry fixture in this slice.
- Do not remove the default fixture mapping mode.
- Do not automatically approve candidate narratives.

## Acceptance

```bash
python -m src.main --fund-code 161725 --provider-mode eastmoney --stock-mapping-mode registry-rule
```

Expected result:

- Generated mappings use `registry_term_rule`.
- Raw/scoring JSON include `stock_mapping_mode`.
- Provider foundation shows `Stock Mappings` from
  `registry-rule-stock-mapping`.
- Reports still disclose Mock fixture layers for the registry, evidence, and
  base signals.
