# Task Handoff

## Goal

Complete MIK-240, MIK-241, and MIK-242 with a JSON + Chinese HTML investigation
gate pack and product shell route.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds `source-investigation-gate-pack-v1`, generated under
`outputs/source_investigation_gates/current/`. It covers:

- MIK-240: China paid provider checklist for Choice, Wind, and iFinD.
- MIK-241: Global paid news/news-analytics checklist for LSEG/Reuters,
  RavenPack, AlphaSense, Benzinga, and Finnhub.
- MIK-242: China community/social access labels for Xueqiu, EastMoney Guba,
  Weibo, and a Stocktwits reference pattern.

The product shell route `/sources/investigation-gates` exposes the report.

## Commands Run

- `uv run pytest tests/test_source_investigation_gate_pack.py -q`
- `uv run pytest tests/test_source_investigation_gate_pack.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run python scripts/run_source_investigation_gate_pack.py --output-dir outputs/source_investigation_gates/current`
- `uv run ruff check .`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `674 passed, 1 skipped`.

## Decision Log

- For MIK-240, selected Choice as the China-first trial target because public
  official pages expose a contact path, Quant API, and cross-platform Python/C++
  support. Wind remains a strong later candidate; iFinD remains later until PM
  obtains a clearer vendor contact/API entitlement path.
- For MIK-241, selected LSEG/Reuters as the professional raw/news candidate,
  RavenPack as the news-analytics candidate, and Benzinga as the lower-cost
  developer API candidate. Finnhub and AlphaSense remain later until exact
  endpoint rights and trial docs are available.
- For MIK-242, allowed only a controlled heat-signal pilot through official API
  or commercial access. Xueqiu and EastMoney Guba are not crawlable until
  permission/TOS/anti-bot status is confirmed. No social/community source is
  marked `trusted_fact`.
- Developer implementation remains blocked for all three issues until PM/vendor
  follow-up provides credentials, API docs, and rights metadata.

## Known Risks And Assumptions

The artifact is based on public official pages and does not replace vendor
quotes, signed terms, credentials, or entitlement-specific API documentation.

## Suggested Quality Checks

- PM should verify vendor contacts and choose the first paid trials.
- Gateway should not receive implementation issues until PM attaches credentials
  and provider docs to Linear.
