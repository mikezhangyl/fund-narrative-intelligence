# Task Brief

## Goal

Complete the M14 product-shell/release user stories that PM/Architect marked as
ready for development:

- `MIK-167`: local release orchestration and verification contract.
- `MIK-163`: operational control panel and config preflight.
- `MIK-164`: one-command local release package.
- `MIK-168`: product shell acceptance and demo checklist.
- `MIK-258`: source quality dashboard integration contract.
- `MIK-259`: source quality dashboard in product shell.

## Scope

- Add deterministic release preflight for demo/live modes.
- Add redacted configuration preflight JSON/Chinese HTML.
- Add one-command release check that generates a manifest and runnable
  acceptance checklist.
- Add source quality dashboard over existing source governance, source schema
  v2, source reliability, and gateway probe artifacts.
- Preserve service boundaries: the shell displays generated artifacts and local
  service contract state; it does not call external providers or recompute
  reliability scores.

## Verification

- `uv run pytest tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py tests/test_source_governance_model.py tests/test_source_reliability_scoring.py tests/test_source_schema_v2.py tests/test_narrative_source_gateway_consumer.py -q`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`
