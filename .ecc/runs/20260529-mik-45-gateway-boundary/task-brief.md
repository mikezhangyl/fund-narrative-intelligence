# Task Brief

## Linear

- Issue: MIK-45
- Title: [ARCH-P0] Gateway-owned market data boundary
- Project: Fund Narrative Intelligence

## Goal

Keep external market-data source expansion owned by the stock-data-gateway
project and make FNI's consumer-side capability inventory explicitly track
gateway ownership, contract coverage, fallback compatibility, and source
disclosure policy.

## Acceptance Focus

- Market-data contract and capability inventory match gateway routes.
- Reports and capability summaries disclose gateway/fallback/degraded source
  posture.
- New external-source work is routed through gateway change requests before FNI
  adds consumption code.
