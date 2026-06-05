# FNI Gateway Source Events

## Objective

Move FNI's narrative source consumption onto the Gateway-owned unified source-event API, keeping FNI responsible for probing, quality display, and downstream intake/report consumption only.

## Implementation Steps

1. Identify current FNI narrative source gateway consumer and probe surfaces.
2. Write failing tests for unified source-event route consumption and structured degradation.
3. Implement the minimal provider/probe changes against the Gateway contract.
4. Update docs/source-quality surfaces for every M20 Gateway source kind.
5. Add downstream FNI artifacts for fresh digest, candidate inbox, and Gateway backlog coverage gaps.
6. Run targeted tests, ruff, and a local probe against stock-data-gateway when available.

## Verification

- `python -m pytest <targeted tests>`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- Gateway-backed probe against `http://127.0.0.1:8700` when the local gateway is running.

## Linear Scope

- `MIK-283`: unified source-event contract conformance probe.
- `MIK-258`: source-quality dashboard first-class coverage rows for all M20 Gateway source kinds.
- `MIK-259` / `MIK-286`: fresh narrative digest reads Gateway source-event probe output, preserves degraded/missing inputs, and emits JSON plus Chinese HTML.
- `MIK-284`: candidate narrative inbox groups Gateway source events without automatic trust promotion.
- `MIK-285`: source coverage gap report separates working, missing, degraded, unsupported, and Later sources for Gateway backlog planning without auto-creating issues.
