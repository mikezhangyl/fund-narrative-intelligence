## Implementation Notes

- Added `src/product_shell/release.py` for release preflight, redacted config
  preflight HTML, release manifest, and acceptance checklist generation.
- Added `scripts/run_product_shell_release_check.py` as the one-command local
  demo/release check.
- Added `src/product_shell/source_quality.py` to join existing source
  governance, source reliability, source schema v2, and gateway probe artifacts
  into a product-shell dashboard.
- Updated `scripts/build_product_shell.py` and route registry so config
  preflight and source quality are first-class generated routes.
- Generated current Chinese HTML/JSON artifacts under
  `outputs/product_shell/round8-current/`.
