# Single Fund Demo

## Goal

Produce real-data, end-to-end demos for selected funds that make the product value visible from one fund page:

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
- Support an explicitly degraded demo path when a real fund has fresh holdings and reviewed mappings but optional provider layers are unavailable.
- Add regression coverage for web-ready payload shape and mock disclosure.
- Run a real `outputs/demo_161725` acceptance output.
- Run a real `outputs/demo_513010` acceptance output for Hong Kong technology platform exposure.

## Out of Scope

- Interactive frontend workflow.
- New provider families.
- Auto-discovery of unrelated narratives.
- User approval mutations in the browser.

## Acceptance

```bash
python scripts/run_single_fund_demo.py --output-dir outputs/demo_161725
python scripts/validate_single_fund_demo.py --output-dir outputs/demo_161725
python scripts/run_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded
python scripts/validate_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded --expected-narrative "Hong Kong Tech Platforms"
```

Expected demo artifacts:

- `outputs/demo_161725/fund_161725_demo.json`
- `outputs/demo_161725/fund_161725_demo.html`
- `outputs/demo_513010/fund_513010_demo.json`
- `outputs/demo_513010/fund_513010_demo.html`

The default demo must fail validation if mock or unavailable layers are present.
Degraded demos must opt in with `--allow-degraded` and must disclose unavailable layers in the HTML data-source section.
