# Risk Notes

- Real Eastmoney holdings can change over time, so primary narrative coverage can drift even though local signal scoring is deterministic.
- V1 still uses fixture-backed evidence and signals for real-fund reports; the calibration is not a substitute for real signal providers.
- The new calibration test scores narratives directly to isolate rule behavior, while the CLI real-smoke command verifies the integrated path against the current live provider response.
- Stage labels remain non-advisory lifecycle classifications and should not be interpreted as buy, sell, or timing recommendations.
