# Single Fund Demo

## Goal

Produce a real-data, end-to-end demo for fund `161725` that makes the product value visible from one fund page:

- top ten real holdings
- reviewed stock-to-narrative mapping
- primary narrative stage and scoring drivers
- evidence and derived signals
- explicit data-source disclosure, including fallback and mock status
- server-side JSON/HTML artifacts ready for a future web approval workspace

## Scope

- Add a reusable single-fund demo artifact builder.
- Add a CLI script that runs the real provider pipeline for `161725`.
- Add a validation script for the generated demo artifacts.
- Add regression coverage for web-ready payload shape and mock disclosure.
- Run a real `outputs/demo_161725` acceptance output.

## Out of Scope

- Interactive frontend workflow.
- New provider families.
- Auto-discovery of unrelated narratives.
- User approval mutations in the browser.

## Acceptance

```bash
python scripts/run_single_fund_demo.py --output-dir outputs/demo_161725
python scripts/validate_single_fund_demo.py --output-dir outputs/demo_161725
```

Expected demo artifacts:

- `outputs/demo_161725/fund_161725_demo.json`
- `outputs/demo_161725/fund_161725_demo.html`

The default demo must fail validation if mock or unavailable layers are present.
