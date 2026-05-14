# News Derived Signals Verification

Status: in progress

Commands:

```bash
python -m pytest tests/test_derived_signals.py tests/test_cli_pipeline.py::test_optional_news_evidence_is_disclosed_and_added_to_outputs tests/test_cli_pipeline.py::test_provider_derived_mode_uses_news_evidence_and_signals -q
```

Result: `11 passed`.

```bash
python -m pytest tests/test_cli_pipeline.py tests/test_derived_signals.py tests/test_provider_derived_enriched_acceptance_script.py tests/test_real_enriched_acceptance_script.py tests/test_registry_rule_enriched_acceptance_script.py -q
```

Result: `62 passed`.

```bash
python -m src.main --fund-code 000001 --include-news-evidence --output-dir outputs/news_signals_000001
python -m src.main --validate-artifact-contracts outputs/news_signals_000001
python -m src.main --build-workspace-snapshot outputs/news_signals_000001
python -m src.main --validate-workspace-snapshot outputs/news_signals_000001/fund_000001_workspace_snapshot.json
python -m src.main --validate-artifact-contracts outputs/news_signals_000001
```

Result: passed; generated `news_evidence`, `derived_signal_events`, and valid
workspace snapshot artifacts.

```bash
python -m ruff check .
python -m compileall -q src tests scripts
python scripts/validate_v1_acceptance.py
python -m coverage run -m pytest && python -m coverage report
```

Result: passed; `234 passed`, total coverage `81%`.

Quality review follow-up fixes:

- Derived provenance now records only providers that actually emitted derived
  signals.
- Provider-derived acceptance scripts now run `--include-news-evidence` and
  validate combined announcement/news evidence.
- Dimension confidence now applies `confidence_multiplier`, matching score
  pressure semantics.
- News signal derivation reason is provider-agnostic.

```bash
python -m pytest tests/test_derived_signals.py tests/test_scoring.py tests/test_cli_pipeline.py::test_provider_derived_mode_uses_news_evidence_and_signals tests/test_provider_derived_enriched_acceptance_script.py tests/test_reviewed_registry_enriched_acceptance_script.py -q
```

Result: `18 passed`.

Post-review full gates:

```bash
python -m ruff check .
python -m compileall -q src tests scripts
python scripts/validate_v1_acceptance.py
python -m coverage run -m pytest && python -m coverage report
```

Result: passed; `235 passed`, total coverage `81%`.
