# Provider-Derived Intelligence Mode

## Goal

Add an optional enriched path that excludes base evidence and signal fixtures,
using provider-derived announcement evidence and derived signals instead.

## Scope

- Keep default fixture-backed evidence and signal behavior unchanged.
- Add `--base-intelligence-mode provider-derived` for single report runs.
- Require CNINFO announcements when provider-derived mode is selected.
- Override `Evidence` and `Signals` provider-foundation layers with
  provider-derived non-mock layers.
- Add a strict live acceptance command for the enriched provider-derived path.

## Non-Goals

- Do not remove default fixture evidence or signal events.
- Do not replace the Narrative Registry fixture in this slice.
- Do not make live-provider acceptance a CI gate.

## Acceptance

```bash
python scripts/validate_provider_derived_enriched_acceptance.py --output-dir outputs/provider_derived_enriched_161725
```

Expected result:

- Evidence input equals generated CNINFO announcement evidence.
- Signal input equals derived signal events.
- Stock mappings use `registry_term_rule`.
- The only remaining mock intelligence foundation layer is Narrative Registry.
