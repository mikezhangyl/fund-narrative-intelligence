# Round 8 Product Shell Execution Plan

Status: implementation complete, verification pending final full-suite gate.

Branch: `codex/round8-product-shell`

ECC run: `.ecc/runs/20260531-round8-product-shell/`

## Scope

- `MIK-165`: route registry and data-source contract with concrete JSON/HTML preview.
- `MIK-166`: artifact index and manifest contract with concrete JSON/Chinese HTML preview.
- `MIK-161`: integrated local product shell navigation.
- `MIK-162`: artifact browser and run history.

## Implemented Surfaces

- `scripts/build_product_shell.py`
- `src/product_shell/route_registry.py`
- `src/product_shell/artifact_index.py`
- `src/product_shell/shell.py`
- `outputs/product_shell/round8-current/route_registry.json`
- `outputs/product_shell/round8-current/route_registry.html`
- `outputs/product_shell/round8-current/artifact_index.json`
- `outputs/product_shell/round8-current/artifact_index.html`
- `outputs/product_shell/round8-current/product_shell.json`
- `outputs/product_shell/round8-current/index.html`
- `outputs/product_shell/round8-current/artifact_browser.html`

## Verification Plan

- Targeted product shell tests.
- Ruff, compileall, full pytest.
- CLI artifact generation.
- ECC run validation.
- Linear evidence and Done state for `MIK-165`, `MIK-166`, `MIK-161`, and `MIK-162`.
