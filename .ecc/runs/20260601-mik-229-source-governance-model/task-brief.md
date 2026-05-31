# Task Brief

## Linear

- Issue: MIK-229
- Title: [ARCH-P0][R13] Source acquisition governance and compliance model

## Scope

Define and implement a deterministic source acquisition governance model. Every
narrative source registry entry must disclose permission, license, retention,
redistribution, anti-bot risk, and owner service before implementation or live
smoke.

## Required Gates

- Crawler-style acquisition modes require robots/TOS review.
- Crawler-style acquisition modes require request pacing policy.
- Prohibited behaviors are explicit blockers: CAPTCHA bypass, stealth browser,
  residential proxy evasion, credential sharing, and login-only scraping without
  permission.

## Verification Notes

- RED: `pytest tests/test_source_governance_model.py -q` failed on missing
  `scripts.run_source_governance_report`.
- GREEN: source governance unit tests passed.
- Full suite: `pytest -q` passed with 599 passed, 1 skipped.
- Chinese HTML report was checked with Playwright DOM evaluation.
