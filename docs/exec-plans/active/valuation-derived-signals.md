# Valuation Derived Signals

## Goal

Make `valuation_risk_score` consume provider valuation metrics instead of only
showing valuation snapshots in artifacts.

## Scope

- Derive deterministic valuation signals from `valuation_snapshots` rows.
- Convert elevated valuation metrics into `valuation_extreme` and discounted
  metrics into `valuation_reset`.
- Add the derived valuation signals to raw/scoring `derived_signal_events` and
  `signal_events`.
- Keep source provenance tied to the valuation provider and stock mapping.

## Non-Goals

- No change to sustainability-score weights.
- No historical valuation percentile model.
- No LLM-based valuation interpretation.

## Acceptance

- Unit tests cover elevated and discounted valuation-derived signals.
- Pipeline tests show valuation metrics move `valuation_risk_score`.
- Reviewed-mapping enriched acceptance still passes with `valuation=eastmoney`.
