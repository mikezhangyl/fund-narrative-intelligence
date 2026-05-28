# Task Brief

Build a Can-Do daily market structure report for FNI that runs independently
from the fund narrative pipeline and emits JSON plus formal reader-facing HTML.

The report combines:

- breadth-window market breadth
- provider-neutral sector heat
- provider-neutral ETF spot heat
- provider-neutral limit-up/down temperature
- gateway Tushare news briefs

The goal for this slice is runnable observability, not strategy, prediction, or
perfect market interpretation.
