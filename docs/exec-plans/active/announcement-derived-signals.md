# Announcement Derived Signals

## Goal

Make optional CNINFO announcement evidence affect scoring through a small,
traceable derived-signal layer.

## Scope

- Convert CNINFO announcement evidence into V1 signal events.
- Keep direct positive/risk announcements mapped to earnings, capital, order, or
  counter-evidence signal types.
- Convert mixed financial/governance disclosures into low-weight momentum
  signals.
- Add `derived_signal_events` to raw and scoring artifacts.
- Add a non-mock `Derived Signals` provider-foundation layer.

## Non-Goals

- Do not parse announcement PDFs.
- Do not replace fixture base signals yet.
- Do not recalibrate every V1 stage threshold.

## Acceptance

```bash
python scripts/validate_announcement_acceptance.py --output-dir outputs/announcement_161725
```

Expected result:

- CNINFO announcement evidence exists.
- Derived signal events exist and are included in raw `signal_events`.
- Scoring uses the combined fixture plus derived signal set.
- Provider foundation discloses `Derived Signals` as non-mock while base
  `Signals` remain fixture-backed.
