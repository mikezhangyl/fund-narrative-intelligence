# Source Table Artifact Verification

Status: passed

Commands:

```bash
python -m pytest tests/test_contracts.py tests/test_main_cli.py tests/test_real_holdings_acceptance_script.py tests/test_real_enriched_acceptance_script.py tests/test_reviewed_registry_enriched_acceptance_script.py tests/test_reviewed_mapping_enriched_acceptance_script.py -q
```

Result: `49 passed`.

```bash
python scripts/validate_v1_acceptance.py
```

Result: passed; generated `fund_000001_source_table.json` and validated the
full artifact bundle.

```bash
python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_161725
```

Result: passed; generated `fund_161725_source_table.json` with reviewed
registry/mapping provenance and no mock layers.

```bash
python -m src.main --validate-artifact-contracts outputs/reviewed_mapping_enriched_161725
```

Result: passed; `manifests=1 source_tables=1 review_queues=1 review_previews=0 persistence_results=0`.

```bash
python -m ruff check .
python -m compileall -q src tests scripts
python -m coverage run -m pytest && python -m coverage report
```

Result: passed; `210 passed`, total coverage `83%`.
