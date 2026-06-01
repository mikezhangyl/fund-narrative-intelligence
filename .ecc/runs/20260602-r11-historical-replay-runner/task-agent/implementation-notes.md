# Implementation Notes

- Added `src/scanners/historical_replay_runner.py` for deterministic artifact replay over a configured date window.
- Added `scripts/run_historical_replay.py` and `config/historical_replay_input.json`.
- Registered `/evaluation/historical-replay` in the product shell.
- Generated current replay artifact from local timeline, digest, quality, and portfolio workspace outputs.
