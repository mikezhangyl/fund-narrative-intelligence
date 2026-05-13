# Risk Notes

## Residual Risks

- Eastmoney is an unofficial/public endpoint and may change without notice.
- The Eastmoney adapter only covers fund holdings; all other intelligence layers remain fixtures.
- Real holdings only produce useful narratives when local stock mappings cover those holdings.
- Coverage tooling remains unavailable in this environment.

## Guardrails

- Explicit `eastmoney` mode avoids changing default mock behavior.
- Fetch failure records `provider_fallback`.
- Provider output is normalized and validated before orchestration.
- Unmapped holdings no longer crash report generation.
