# Risk Notes

- The FNI worktree was already heavily dirty, including untracked market-data
  source files. Changes were kept to the existing market-data source layer,
  related scripts, and focused tests.
- Live gateway/provider smoke checks were not run; verification used fake
  fetchers and full local tests.
- The news smoke command reports Tushare permission errors as report status
  instead of failing before writing artifacts.
