# Risk Notes

- The artifact index is file-system based and deterministic for local outputs;
  it is not a database or hosted artifact service.
- The route registry exposes planned shell routes, but only the static product
  home and artifact browser are implemented in this slice.
- The current artifact browser shows safe local paths rather than opening files
  through an HTTP file server.
- Future Round 8 work for config preflight and release packaging must preserve
  secret redaction and avoid moving provider or scoring logic into the shell.
