# FNI Gateway Source Events

## Objective

Move FNI's narrative source consumption onto the Gateway-owned unified source-event API, keeping FNI responsible for probing, quality display, and downstream intake/report consumption only.

## Implementation Steps

1. Identify current FNI narrative source gateway consumer and probe surfaces.
2. Write failing tests for unified source-event route consumption and structured degradation.
3. Implement the minimal provider/probe changes against the Gateway contract.
4. Update docs/source-quality surfaces only where needed for the new route.
5. Run targeted tests, ruff, and a local probe against stock-data-gateway when available.

## Verification

- `python -m pytest <targeted tests>`
- `python -m ruff check .`
- Gateway-backed probe against `http://127.0.0.1:8700` when the local gateway is running.
