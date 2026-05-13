# Task Brief

## Goal

Expose per-fund mapping precision flag counts in the real-smoke CLI output.

## Scope

- Add `precision_flags=<count>` to each `--run-real-smoke` stdout line.
- Keep the field backward-compatible when summary data lacks the count.
- Update documentation and project memory.

## Acceptance

- CLI tests cover the new stdout field.
- Full quality gates and smoke commands pass.

## Verification

- `python -m pytest tests/test_main_cli.py::test_main_run_real_smoke_returns_status -q`
- `python -m ruff check .`
- `python -m coverage run -m pytest -q`
- `python -m coverage report` (`87%`)
- `python -m compileall -q src tests scripts`
- `python -m src.main --run-real-smoke`
- `python -m src.main --run-announcement-smoke`

## Outcome

`python -m src.main --run-real-smoke` now prints `precision_flags=<count>` per fund. The latest smoke output shows zero flags for baijiu, healthcare, and real estate; two for semiconductor, one for new energy, and two for defense.
