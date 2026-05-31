# Round 8 Product Shell and Artifact Browser Acceptance - 2026-05-31

Canonical readable artifact:
`docs/product/round8-product-shell-artifact-browser-acceptance-2026-05-31.html`

Implemented:

- `product-shell-route-registry-v1` route registry with owner service, data
  source type, freshness/degradation metadata, and shell client policy.
- `product-shell-artifact-index-v1` artifact index over existing `outputs/`
  JSON/HTML artifacts with safe relative links.
- `product-shell-v1` local product home.
- Chinese HTML artifact browser.

Primary command:

```bash
uv run python scripts/build_product_shell.py --artifact-root outputs --output-dir outputs/product_shell/round8-current
```

Generated artifacts:

- `outputs/product_shell/round8-current/route_registry.json`
- `outputs/product_shell/round8-current/route_registry.html`
- `outputs/product_shell/round8-current/artifact_index.json`
- `outputs/product_shell/round8-current/artifact_index.html`
- `outputs/product_shell/round8-current/product_shell.json`
- `outputs/product_shell/round8-current/index.html`
- `outputs/product_shell/round8-current/artifact_browser.html`

Boundary: the shell does not recalculate radar, quality, portfolio exposure, or
provider data. It only consumes existing APIs and generated artifacts.
