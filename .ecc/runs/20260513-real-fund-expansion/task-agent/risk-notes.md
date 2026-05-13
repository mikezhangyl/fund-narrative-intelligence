# Risk Notes

## Residual Risks

- Eastmoney/Tiantian Fund is a public no-key endpoint, so schema or availability can change outside project control.
- Real-fund scoring still uses local fixture-backed evidence and signals; only holdings are live in V1.
- Registry-term fallback mapping is deterministic but coarse, so it can over-map sector holdings when industry labels are broad.
- `000991` currently passes the smoke threshold with 78% coverage, close to the configured 75% floor.

## Mitigations

- Per-fund smoke failures now write summary artifacts and keep the rest of the smoke set running.
- Mapping coverage, method counts, and unmapped holdings are surfaced in JSON and report outputs.
- The smoke command returns non-zero when any fund fails or falls below the coverage threshold.
