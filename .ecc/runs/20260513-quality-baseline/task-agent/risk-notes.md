# Risk Notes

## Residual Risks

- Tool versions are pinned in `pyproject.toml`; this is reproducible enough for V1, but a lockfile would be stronger once dependency management is formalized.
- Coverage is aggregate over `src`; `src/main.py` remains at 76% and some error branches are still uncovered.
- CLI tests assert a few stable console strings, so harmless wording changes may require test updates.

## Mitigations

- Coverage threshold is configured in one place: `pyproject.toml`.
- README no longer overrides coverage threshold with a command-line flag.
- Real-provider network smoke remains separate from the unit coverage gate.
