## Goal

Complete ready M14 product-shell/release stories and source quality dashboard
integration.

## Completed Linear Issues

- `MIK-167`
- `MIK-163`
- `MIK-164`
- `MIK-168`
- `MIK-258`
- `MIK-259`

## User-Visible Artifacts

- `outputs/product_shell/round8-current/index.html`
- `outputs/product_shell/round8-current/config_preflight.html`
- `outputs/product_shell/round8-current/release_manifest.html`
- `outputs/product_shell/round8-current/acceptance_checklist.html`
- `outputs/product_shell/round8-current/source_quality_dashboard.html`

## Files Changed

See `changed-files.txt`.

## Implementation Summary

Added release/preflight primitives, a one-command release check, current
release artifacts, and a source quality dashboard that consumes existing source
artifacts without provider access or score recomputation.

## Commands Run

- `uv run pytest tests/test_product_shell.py tests/test_product_shell_release.py tests/test_product_shell_source_quality.py tests/test_source_governance_model.py tests/test_source_reliability_scoring.py tests/test_source_schema_v2.py tests/test_narrative_source_gateway_consumer.py -q`
- `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- `uv run pytest`
- `uv run ruff check .`
- `git diff --check`

## Verification

- Focused product-shell/source tests: `44 passed`
- Full suite: `608 passed, 1 skipped`
- `uv run ruff check .`: passed
- `git diff --check`: passed

## Test Results

All verification commands passed.

## Known Risks And Assumptions

`source_quality_dashboard` can report `degraded` while demo release acceptance
passes, because it is showing source warnings and blocked governance states
rather than failing the shell build.

## Suggested Quality Checks

- Re-run `uv run python scripts/run_product_shell_release_check.py --mode demo --output-dir outputs/product_shell/round8-current`
- Re-run `uv run pytest`

## Notes

No new provider acquisition was added. The source quality dashboard consumes
existing artifacts and gateway probe output only.
