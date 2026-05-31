# Implementation Notes

Round 8 product shell work produced concrete, inspectable artifacts before UI
work:

- `product-shell-route-registry-v1` declares pages, owners, data-source types,
  freshness/degradation labels, and shell-side forbidden logic.
- `product-shell-artifact-index-v1` scans existing `outputs/` JSON/HTML files,
  excludes credential-like and temporary/log paths, emits safe relative links,
  and marks superseded artifacts.
- `product-shell-v1` combines the route registry and artifact index into a
  static local product home and artifact browser.

The implementation remains Python/static HTML. It does not introduce provider
fetching, narrative scoring, quality scoring, or portfolio aggregation into the
shell layer.
