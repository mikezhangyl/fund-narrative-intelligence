# Round 4 Live Provider Credential Smoke - 2026-05-30

Canonical readable artifact:
`docs/product/round4-live-provider-credential-smoke-2026-05-30.html`

Linear issues: `MIK-93`, `MIK-88`

Implemented surface:

```bash
uv run python scripts/run_live_validation_dashboard.py
```

Fixture acceptance:

```bash
uv run python scripts/run_live_validation_dashboard.py --output-dir outputs/live_validation_dashboard/2026-05-30-mik-93-88-fixture
```

The output contract uses the Round 4 credential-safe status taxonomy and never
returns secret values.
