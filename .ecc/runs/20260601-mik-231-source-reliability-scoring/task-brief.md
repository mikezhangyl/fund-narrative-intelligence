# Task Brief

## Linear

- Issue: MIK-231
- Title: [ARCH-P0][R13] Source reliability, licensing, and anti-bot risk scoring

## Scope

Define deterministic source scoring across availability, latency/freshness,
schema stability, completeness, entity tagging quality, license clarity,
anti-bot risk, retry recoverability, historical depth, operational cost, and
contradiction rate.

## Labels

The scoring output must use: Trusted Fact, Licensed News, Research Context,
Heat Signal, Experimental, Avoid.

## Trust Boundary

Social/community sources without corroborating evidence are capped at Heat
Signal and cannot receive Trusted Fact.

## Verification Notes

- RED: `pytest tests/test_source_reliability_scoring.py -q` failed on missing
  `scripts.run_source_reliability_report`.
- GREEN targeted: `pytest tests/test_source_reliability_scoring.py -q`.
- Full suite: `pytest -q` passed with 612 passed, 1 skipped.
- Chinese HTML report was checked with Playwright DOM evaluation.
