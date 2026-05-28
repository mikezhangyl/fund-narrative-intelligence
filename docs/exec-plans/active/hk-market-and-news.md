# HK Market And News

## Goal

Improve the real single-fund Hong Kong demo slice without expanding into a full
new provider program.

- make Hong Kong stock quote lookup stop using A-share symbol rules
- keep unsupported Hong Kong valuation and financial paths explicit instead of
  retrying A-share endpoints
- expand default news evidence beyond Google News RSS by adding Sina Finance
- preserve the reviewed single-fund demo workflow for `513010` and `161725`

## Scope

- Add a shared stock-market resolver for provider symbol formatting.
- Route Hong Kong quote lookup to the correct Yahoo Finance HK symbols.
- Mark Eastmoney valuation and financial metrics as unsupported for Hong Kong
  stock codes.
- Add a Sina Finance roll news provider.
- Add a multi-source news provider and make it the default news evidence path.
- Validate the result through single-fund demo outputs.

## Out Of Scope

- HKEX announcements provider
- Hong Kong valuation metrics provider
- Hong Kong financial metrics provider

## Acceptance

```bash
python scripts/run_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded
python scripts/validate_single_fund_demo.py --fund-code 513010 --output-dir outputs/demo_513010 --allow-degraded --expected-narrative "Hong Kong Tech Platforms"
python scripts/run_single_fund_demo.py --output-dir outputs/demo_161725
python scripts/validate_single_fund_demo.py --output-dir outputs/demo_161725 --expected-narrative "Premium Baijiu Consumption"
```

Expected result:

- `513010` market quotes become non-empty and non-mock
- `513010` valuation and financial metrics remain explicit `unavailable`
- `513010` and `161725` news evidence use the default multi-source provider
