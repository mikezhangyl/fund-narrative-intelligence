# Task Brief

## Goal

Complete all current Round 2 and Round 3 Linear requirements for the Fund
Narrative Intelligence project.

## Branch

`codex/round2-3-linear-develop`

## Source Requirements

- Round 2: `MIK-52` to `MIK-67`, covering live validation, source expansion,
  fund intelligence workflows, and durable operations/governance.
- Round 3: `MIK-68`, `MIK-69`, and formal child issues `MIK-74` to `MIK-85`,
  covering Narrative Radar Service ownership, scoring, mining, API contract,
  evidence drill-down, preview, and optional AI explanation.

## Execution Plan

Use `docs/exec-plans/active/round2-round3-linear-execution.md` as the controlling
plan. Work in user-story-sized slices with TDD, checkpoint commits, Linear
comments, and Linear Done transitions after verification.

## Initial Decisions

- Reuse the existing `codex/narrative-radar-planning` planning commits as the
  base for the execution branch.
- Use one long-lived execution branch for Round 2 / Round 3 rather than creating
  a branch per milestone.
- Treat early Round 3 PM issues `MIK-70` to `MIK-73` as possible duplicates of
  the formal `MIK-74` to `MIK-85` plan, to be resolved during Round 3 closeout.
