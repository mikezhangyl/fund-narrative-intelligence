# Real Holdings Acceptance

## Goal

Add a strict manual acceptance path for the first partially real V1 run:
Eastmoney fund holdings with fixture-backed intelligence layers.

## Scope

- Run fund `161725` through `--provider-mode eastmoney`.
- Validate generated artifact contracts.
- Fail if Eastmoney holdings fall back to mock.
- Confirm reports visibly disclose the mixed Eastmoney + Mock fixture foundation.
- Keep this command outside CI because it depends on a live provider.

## Non-Goals

- Do not replace registry, mapping, evidence, or signal fixtures yet.
- Do not add web interaction yet.
- Do not make live-provider checks part of GitHub Actions.

## Acceptance

```bash
python scripts/validate_real_holdings_acceptance.py --output-dir outputs/real_161725
```

Expected result:

- Raw holdings provider is `eastmoney-fundmobapi`.
- Holdings layer is `fresh` and not mock.
- Registry, stock mappings, evidence, and signals remain mock-backed with
  `mock://fixtures/...` source URLs.
- Overall run quality is `partial`.
- Markdown and HTML reports include the mixed source notice.
