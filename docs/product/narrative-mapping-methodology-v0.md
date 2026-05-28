# Narrative Mapping Methodology v0

## Purpose

This document defines the minimum method for assigning stocks to market
narratives in FNI. It exists because the current reviewed narrative registry and
stock-to-narrative mappings are explicitly `untrusted_experimental`: they are
useful local seeds, but their source chain, mapping logic, and validation
criteria are not yet strong enough to treat as trusted production knowledge.

## User Story

As a market-structure analyst, I want every stock-to-narrative mapping to have a
clear evidence chain, repeatable logic, and explicit exclusions, so that fund
narrative exposure reports can be audited instead of relying on hand-waved
labels.

## Trust States

- `candidate_untrusted`: proposed by rules, data, or a model; not accepted.
- `reviewed_untrusted`: reviewed enough for experiments, but not methodologically
  proven.
- `trusted_validated`: accepted only after evidence, rationale, exclusions, and
  audit checks pass.

The current reviewed registry and reviewed mapping store remain
`untrusted_experimental` until promoted through a dedicated audit.

## 股票事实层

Every mapping should be grounded in stock-level facts. Acceptable fact sources
include:

-主营业务 and product/service descriptions.
- Industry and concept-board memberships.
- Financial-report keywords and segment exposure.
- Announcements and material events.
- Fund/ETF/index constituent relationships.
- Capital-flow, volume, and market-attention context when used only as support.

No mapping should be promoted from stock name, market nickname, or a single
headline alone.

## 候选叙事生成

Candidate narratives should be generated from repeated facts, not from one-off
labels:

- A candidate should have multiple supporting facts or multiple related stocks.
- The candidate name should describe a market structure or business driver, not
  merely a company name.
- Broad parent narratives and narrow child narratives should be separated.
- Candidate generation may use models, but model output is only a proposal.

## 映射打分

Each stock-to-narrative mapping should expose these components:

- Business relevance: how directly the company participates in the narrative.
- Evidence count: how many independent facts support the mapping.
- Evidence quality: whether the evidence is official, structured, repeated, and
  recent.
- Specificity: whether the narrative is more precise than a broad industry tag.
- Durability: whether the mapping is stable or only event-driven.
- Recency: whether the current evidence still supports the mapping.

Confidence values must remain heuristic until this scoring model is calibrated.

## 反例和排除

Every trusted mapping needs exclusion logic:

- Why the stock does not belong to nearby narratives.
- Why a broad sector label is not sufficient.
- Why a one-time event should not dominate a durable mapping.
- Example: communication equipment is not automatically optical modules.
- Example: semiconductor is not automatically AI infrastructure.

## 人工审核入口

The system may create candidate mappings, but promotion requires review:

- Candidate mapping starts as `candidate_untrusted`.
- Reviewer must see evidence, rationale, exclusions, and confidence components.
- Reviewer can approve, reject, or request more evidence.
- Approval without full source-and-logic audit keeps the mapping
  `reviewed_untrusted`, not `trusted_validated`.

## Minimum Trusted Promotion Bar

A mapping store can be promoted to `trusted_validated` only when:

- Every active narrative has a source chain and promotion rationale.
- Every mapping has evidence references and formal rationale.
- Every mapping has at least one exclusion or negative test.
- Undefined narrative IDs are zero.
- A representative fund-holding audit shows coverage and contradiction risks.
- The audit result is reproducible from stored inputs.

## Current Expected Outcome

The current audit should remain blocked. That is intentional. The first goal is
to make untrusted assumptions visible and machine-checkable before expanding the
mapping store.
