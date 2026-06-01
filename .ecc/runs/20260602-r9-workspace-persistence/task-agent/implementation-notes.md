# Implementation Notes

- Added `src/product_shell/workspace_store.py` with a `WorkspaceRepository` protocol and JSON-file repository implementation.
- Added immutable saved-view upsert behavior with surface allow-listing and recursive secret-key rejection.
- Added `scripts/manage_product_workspace.py save-view` for local operators to persist saved views and generate Chinese HTML.
- Integrated workspace state into `scripts/build_product_shell.py`, `product_shell.json`, `index.html`, and the route registry.
- Generated `outputs/product_shell/round8-current/workspace_state.json` and `.html` with a current artifact-review saved view.

The store is local user state only; it does not mutate trusted market data, Narrative Service records, or provider-owned artifacts.
