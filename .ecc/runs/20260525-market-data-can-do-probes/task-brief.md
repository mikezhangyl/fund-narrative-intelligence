# Task Brief

## Goal

Complete the FNI consumer-side Can-Do probe layer from
`docs/exec-plans/active/market-data-can-do-roadmap.md` after the local gateway
exposes the requested provider-neutral endpoints.

## Scope

- Route FNI local gateway source methods to provider-neutral sector and
  limit-up/down endpoints.
- Add gateway-backed ETF spot and Tushare news brief source methods.
- Add one runnable command each for ETF spot, limit-up/down, and news smoke
  reports, complementing existing breadth and sector commands.
- Keep changes scoped to the existing market-data source layer, scripts, and
  focused tests.

## Constraints

- Do not add direct AkShare, EastMoney, Tushare, or news-site integrations.
- Do not clean up unrelated dirty worktree changes.
- Commands must emit JSON and Markdown reports under `outputs/` by default.
