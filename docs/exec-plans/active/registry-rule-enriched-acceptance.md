# Registry Rule Enriched Acceptance

## Goal

Add a strict live-provider acceptance gate for the enriched path when stock
mappings are derived at runtime from Narrative Registry terms.

## Scope

- Run Eastmoney holdings with `--stock-mapping-mode registry-rule`.
- Include CNINFO announcement evidence and market quote snapshots.
- Validate the normal enriched real-provider contract.
- Require all selected stock mappings to use `registry_term_rule`.
- Require the `Stock Mappings` provider layer to be
  `registry-rule-stock-mapping`.

## Non-Goals

- Do not make this live-provider check a CI gate.
- Do not remove default fixture mapping mode.
- Do not replace the Narrative Registry fixture yet.

## Acceptance

```bash
python scripts/validate_registry_rule_enriched_acceptance.py --output-dir outputs/registry_rule_enriched_161725
```

Expected result:

- Eastmoney holdings, CNINFO evidence, market quotes, and derived signals are
  fresh.
- Selected mappings are runtime `registry_term_rule` mappings.
- Reports disclose runtime stock mappings and remaining Mock fixture layers.
