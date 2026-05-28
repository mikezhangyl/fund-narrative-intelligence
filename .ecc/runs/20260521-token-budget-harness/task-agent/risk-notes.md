# Risk Notes

- `docs/exec-plans/active/` still contains historical files. This is intentional to avoid breaking existing run references; startup code and instructions now use the curated `index.md`.
- Full memory files remain large. This is intentional; they are now on-demand references instead of default startup files.
- This task did not start a separate Quality Agent. The change is parent-executed and verified with tests, lint, compile checks, bounded output checks, and self-review.
