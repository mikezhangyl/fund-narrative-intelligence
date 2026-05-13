# Product Documents

This directory contains product and architecture source documents for Fund Narrative Intelligence.

## Canonical Sources

- [Fund Narrative Intelligence System](./fund-narrative-intelligence-system.html)
- [V1 Implementation Spec](./v1-implementation-spec.md)

## Current Product Definition

The system analyzes a fund through its holdings to identify market narratives, evaluate narrative sustainability, and produce an evidence-backed report. V1 is report-first, monolith-first, and mock-provider capable.

The first implementation loop is:

`Fund -> Holdings -> Stock Mapping -> Narrative Aggregation -> Signal-backed Narrative State -> Evidence Report`

The system must not present output as investment advice or produce buy/sell signals.

The first engineering acceptance command is:

```bash
python -m src.main --fund-code 000001
```

It must produce raw JSON, scoring JSON, Markdown report, and HTML report artifacts under `outputs/`.

V1 can also list available mock fixtures:

```bash
python -m src.main --list-fixtures
```

And run all local mock scenarios:

```bash
python -m src.main --run-all-fixtures
```
