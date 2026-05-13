# Task Brief

## Goal

Add optional announcement-to-evidence conversion for CNINFO-style announcement metadata.

## Scope

- Add deterministic conversion from announcement metadata into V1 evidence records.
- Map announcements to narrative IDs through existing stock narrative mappings.
- Classify title/category metadata into conservative evidence types and sentiments.
- Preserve provider data quality and mapping confidence in evidence confidence.
- Keep conversion optional and outside the default report pipeline.

## Out Of Scope

- PDF download or parsing.
- Real announcement orchestration in `run_pipeline`.
- Signal generation from announcement evidence.
- Any investment recommendation language.

## Required Verification

- `python -m pytest tests/test_announcement_evidence.py -q`
- `python -m ruff check .`
- `python -m compileall -q src tests scripts`
- `python -m coverage run -m pytest -q && python -m coverage report`
- `python -m src.main --run-real-smoke`
- `python -m src.main --fund-code 000001`
