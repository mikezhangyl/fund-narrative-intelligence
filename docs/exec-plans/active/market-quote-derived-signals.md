# Market Quote Derived Signals

## Goal

Make optional market quote snapshots affect scoring through conservative,
traceable derived signals.

## Scope

- Convert quote change percentages into relative strength signals.
- Add `relative_strength_down` as a capital-score negative signal type.
- Add market quote derived events to raw/scoring `derived_signal_events`.
- Include derived quote signals in raw `signal_events` and scoring input.
- Keep quote-derived signals separate from fixture base signals in provider
  provenance.

## Non-Goals

- Do not build a full technical-analysis model.
- Do not use intraday tick data.
- Do not replace fixture signal providers yet.

## Acceptance

```bash
python scripts/validate_market_quotes_acceptance.py --output-dir outputs/market_quotes_161725
```

Expected result:

- Market quote rows exist.
- Derived quote signals exist and are included in raw `signal_events`.
- Provider foundation discloses non-mock `Derived Signals`.
- Base fixture signals remain explicitly mock-backed.
