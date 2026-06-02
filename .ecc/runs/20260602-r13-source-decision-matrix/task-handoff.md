# Task Handoff

## Goal

Complete R13 source deep-mining planning and architecture user stories with a
real decision matrix artifact and product shell route.

## Files Changed

See `changed-files.txt`.

## Implementation Summary

The slice adds `narrative-source-decision-matrix-v1`, generated as JSON and
Chinese HTML. It covers licensed news/market-intelligence providers, official
disclosure/regulator sources, public web/industry crawler pilots, and
community/social heat sources. The matrix records decision labels, owner
service, Gateway/FNI boundaries, permission gates, anti-bot risk, retention
policy, and v2 source-event / narrative-fact / candidate-narrative contract
fields.

FNI remains display/consumer-only for provider/source acquisition. Paid provider
trial work and social/community permission checks are marked as PM investigation
gates before any gateway implementation.

## Commands Run

- `uv run pytest tests/test_narrative_source_decision_matrix.py -q`
- `uv run pytest tests/test_narrative_source_decision_matrix.py tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py -q`
- `uv run ruff check .`
- `uv run python scripts/run_narrative_source_decision_matrix.py --output-dir outputs/narrative_source_decision_matrix/current`
- `uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `git diff --check`

## Test Results

Full suite: `660 passed, 1 skipped`.

## Known Risks And Assumptions

Provider trial/contact paths, current commercial terms, and permission-specific
API documentation were not implemented in FNI. Those remain PM investigation
inputs before any Gateway adapter can be assigned.

## Suggested Quality Checks

- PM should review the paid-provider rows before marking provider integration
  dev-ready.
- Gateway should use the contract fields when creating future source-event
  adapters.
