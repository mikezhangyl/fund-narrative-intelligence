# Valuation Snapshot Provider Verification

Status: passed

Commands:

```bash
python -m pytest tests/test_cli_pipeline.py tests/test_intelligence_providers.py tests/test_workspace_snapshot.py -q
```

Result: `61 passed`.

```bash
python -m src.main --fund-code 000001 --include-market-quotes --include-valuation-snapshots --output-dir outputs/valuation_context_000001
python -m src.main --validate-artifact-contracts outputs/valuation_context_000001
```

Result: passed; generated raw/scoring artifacts with `valuation_snapshots` and
a `Valuation` provider layer.

```bash
python -m src.main --build-workspace-snapshot outputs/valuation_context_000001
python -m src.main --validate-workspace-snapshot outputs/valuation_context_000001/fund_000001_workspace_snapshot.json
python -m src.main --validate-artifact-contracts outputs/valuation_context_000001
```

Result: passed; workspace snapshot preserves valuation provider disclosure.

Reviewer follow-up fixes:

- Report Markdown/HTML now surface provider-layer notes, including the
  quote-derived valuation disclaimer.
- Valuation contracts require `quote-derived-valuation`,
  `quote-derived-valuation-v1`, and item-level `source_provider`, `source_url`,
  and `retrieved_at`.
- Valuation provider layer marks `is_mock` when its source quality is mock.
- Workspace snapshot tests cover a valuation-enabled run.

```bash
python -m ruff check .
python -m compileall -q src tests scripts
python scripts/validate_v1_acceptance.py
python -m coverage run -m pytest && python -m coverage report
```

Result: passed; `223 passed`, total coverage `81%`.
