# News Evidence Provider Verification

Status: passed

Commands:

```bash
python -m pytest tests/test_news_provider.py tests/test_cli_pipeline.py::test_cli_include_news_evidence_passes_option_to_pipeline tests/test_cli_pipeline.py::test_optional_news_evidence_is_disclosed_and_added_to_outputs tests/test_intelligence_providers.py::test_reserved_mock_source_providers_return_stable_empty_payloads -q
```

Result: `6 passed`.

```bash
python -m pytest tests/test_cli_pipeline.py tests/test_news_provider.py tests/test_intelligence_providers.py tests/test_workspace_snapshot.py -q
```

Result: `68 passed`.

```bash
python -m src.main --fund-code 000001 --include-news-evidence --output-dir outputs/news_evidence_000001
python -m src.main --validate-artifact-contracts outputs/news_evidence_000001
python -m src.main --build-workspace-snapshot outputs/news_evidence_000001
python -m src.main --validate-workspace-snapshot outputs/news_evidence_000001/fund_000001_workspace_snapshot.json
python -m src.main --validate-artifact-contracts outputs/news_evidence_000001
```

Result: passed; generated `news_evidence`, a `News Evidence` provider layer,
visible RSS title/snippet disclosure, and a valid workspace snapshot.

```bash
python -m ruff check .
python -m compileall -q src tests scripts
python scripts/validate_v1_acceptance.py
python -m coverage run -m pytest && python -m coverage report
```

Result: passed; `229 passed`, total coverage `81%`.

Quality review follow-up fixes:

- `MockNewsEvidenceProvider` now returns the full `news-evidence-v1` contract
  with mock source URL disclosure.
- `validate_news_evidence_payload` is provider-agnostic and accepts disclosed
  mock payloads while enforcing the shared news evidence shape.
- `query_scope` records requested, queried, and omitted narrative IDs so reports
  can disclose top-N query coverage.
- Workspace snapshot build validates optional `news_evidence` payloads and
  rejects invalid raw/scoring bundles.

```bash
python -m pytest tests/test_news_provider.py tests/test_cli_pipeline.py::test_optional_news_evidence_is_disclosed_and_added_to_outputs tests/test_workspace_snapshot.py::test_workspace_snapshot_preserves_news_layer_for_future_web tests/test_workspace_snapshot.py::test_build_workspace_snapshot_rejects_invalid_news_payload tests/test_intelligence_providers.py::test_reserved_mock_source_providers_return_stable_empty_payloads -q
```

Result: `7 passed`.
