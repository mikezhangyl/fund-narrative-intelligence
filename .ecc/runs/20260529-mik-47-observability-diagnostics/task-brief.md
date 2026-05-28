# MIK-47 Observability Diagnostics

Linear: MIK-47 `[ARCH-P1] Observability and operational diagnostics model`

Scope:

- Define a lightweight `narrative-operational-diagnostics-v1` schema.
- Expose diagnostics from `GET /api/v1/narratives/ops/summary`.
- Add classified structured warnings for runtime failures and data gaps.
- Document the observability policy without introducing proxy, browser, or
  anti-detect infrastructure.

Verification is recorded in `verification.md`.
