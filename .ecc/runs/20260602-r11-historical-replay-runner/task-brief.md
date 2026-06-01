# Task Brief

Task run: 20260602-r11-historical-replay-runner

Linear scope:

- MIK-189: Historical replay runner
- MIK-192: Replay input and run schema

Goal: add a deterministic, bounded, resumable historical replay runner over local artifacts for source events, radar snapshots, quality findings, portfolio exposure, and alert outputs.

Boundary: replay is system-quality evaluation only. It is not a trading backtest, return predictor, portfolio optimizer, or provider fetcher.
