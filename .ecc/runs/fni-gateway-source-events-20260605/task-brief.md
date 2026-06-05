# Task Brief

## Goal

Consume the newly merged stock-data-gateway narrative source-event API from FNI without reintroducing direct SEC, CNINFO, GDELT, RSS, industry-media, or social-source acquisition inside FNI.

## Scope

- Add or update FNI gateway client code for provider-neutral narrative source events.
- Add tests first for the expected gateway contract and FNI degradation behavior.
- Keep FNI as consumer/reporting surface only; acquisition remains gateway-owned.
- Verify with targeted tests, ruff, and relevant probe/report scripts.

## Non-Goals

- Do not add direct public website crawlers in FNI.
- Do not promote source events into trusted narratives automatically.
- Do not require live external credentials.

## References

- Gateway PR: https://github.com/mikezhangyl/stock-date-gateway/pull/1
- Gateway route: `/api/v1/market-data/narrative/source-events`
- Gateway branch merged into main at `8259058ab1eb4f31c70fe722d2b4a1f0cb2b2847`.
