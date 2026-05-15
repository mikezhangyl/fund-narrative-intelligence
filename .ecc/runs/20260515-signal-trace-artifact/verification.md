# Signal Trace Artifact Verification

Status: passed

Commands:

- `python -m pytest tests/test_cli_pipeline.py::test_cli_generates_required_v1_artifacts tests/test_workspace_snapshot.py::test_build_workspace_snapshot_from_output_directory tests/test_workspace_snapshot.py::test_workspace_snapshot_validation_rejects_signal_trace_identity_drift -q` - passed, 3 tests.
- `python -m pytest tests/test_cli_pipeline.py::test_artifact_contracts_reject_signal_trace_identity_mismatch -q` - passed, 1 test.
- `python -m pytest tests/test_cli_pipeline.py tests/test_workspace_snapshot.py tests/test_main_cli.py tests/test_v1_acceptance_script.py -q` - passed, 91 tests.
- `python scripts/validate_v1_acceptance.py` - passed and generated `fund_000001_signal_trace.json`.
- `python scripts/validate_reviewed_mapping_enriched_acceptance.py --output-dir outputs/reviewed_mapping_enriched_acceptance` - passed and generated `fund_161725_signal_trace.json`.
- `python -m ruff check .` - passed.
- `python -m compileall -q src tests scripts` - passed.
- `python -m coverage run -m pytest -q && python -m coverage report` - passed, 247 tests, total coverage 80%.

Acceptance evidence:

- Mock V1 acceptance validates `signal_trace` in artifact contracts and embeds it in the workspace snapshot.
- Reviewed-mapping enriched acceptance validates that the signal trace includes `valuation_snapshot` signals from `eastmoney-valuation`.
- Mock baseline signal traces fall back to `mock://fixtures/signal_events.json` for fixture signal events without event-level source URLs.
