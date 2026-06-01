# Task Brief

Task run: 20260602-r10-research-export-pack

Linear scope:

- MIK-185: Analyst notes and research export pack
- MIK-188: Analyst note and research export contract

Goal: generate a cited research export pack from existing narrative research workbench artifacts, with an analyst-note contract that treats notes as auditable user artifacts and prevents notes from promoting trusted state.

Boundary:

- FNI reads local timeline/search and evidence graph artifacts only.
- FNI does not access providers or recompute narrative quality.
- User notes can be linked to narratives, source events, or comparison objects, but their promotion effect is always `none`.
