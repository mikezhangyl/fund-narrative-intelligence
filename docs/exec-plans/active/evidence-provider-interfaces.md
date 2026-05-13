# Evidence Provider Interfaces Execution Plan

## Purpose

Create explicit V1 provider-layer interfaces for fixture-backed intelligence sources and reserved future real providers.

## Scope

- Add mock layer providers for narrative registry, stock mappings, evidence, and signal events.
- Add reserved mock interfaces for market data, valuation, announcements, and news evidence.
- Wire `MockDataProvider` through the layer providers without changing CLI behavior.
- Keep all reserved providers honest by returning explicit empty mock payloads.
- Update docs and memory with the provider-layer contract.

## Acceptance

- Existing mock and Eastmoney pipeline commands still pass.
- Layer provider contract tests pass.
- Provider foundation still marks mock layers accurately.
- Full quality gates pass.

## Status

Implemented locally; final verification and run artifact closure pending.

## Run Record

- `.ecc/runs/20260513-evidence-provider-interfaces/`
