# Workspace Snapshot Loader Verification

Status: passed

Commands:

```bash
python -m pytest tests/test_workspace_snapshot.py tests/test_main_cli.py::test_main_builds_and_validates_workspace_snapshot -q
```

Result: `7 passed`.

```bash
python -m src.main --build-workspace-snapshot outputs/reviewed_mapping_enriched_161725
python -m src.main --validate-workspace-snapshot outputs/reviewed_mapping_enriched_161725/fund_161725_workspace_snapshot.json
```

Result: passed; built and validated the reviewed-mapping enriched workspace
snapshot, then validated the enclosing artifact directory with
`workspace_snapshots=1`.

```bash
python -m ruff check .
python -m compileall -q src tests scripts
python scripts/validate_v1_acceptance.py
python -m coverage run -m pytest && python -m coverage report
```

Result: passed; `213 passed`, total coverage `82%`.

Reviewer findings fixed:

- Broken report links are rejected before snapshot build.
- Explicit snapshot output must stay in the artifact directory.
- Review queue identity is validated against snapshot identity.
- Primary narrative and mapping coverage fields have minimum loader contracts.

Final full-suite result after review fixes: `217 passed`, total coverage `82%`.
