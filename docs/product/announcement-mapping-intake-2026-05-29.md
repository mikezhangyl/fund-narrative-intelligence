# Announcement Mapping Intake - 2026-05-29

## Scope

This slice implements the Round 2 MIK-56 workflow for turning structured
company announcement events into reviewable stock-to-narrative mapping evidence
candidates.

The workflow accepts `source-event-schema-v1` events with
`source_type=announcement`. It assumes the upstream provider has already
supplied structured title, summary, stock code, date, and source URL fields. It
does not make PDF parsing quality promises and does not extract financial facts
unless those facts are already present in the structured summary or claim list.

## Entry Point

```bash
uv run python scripts/run_announcement_mapping_intake.py \
  --output-dir outputs/announcement_mapping_intake/2026-05-29-mik-56-fixture
```

By default, the script reads
`data/fixtures/announcement_events_for_mapping_intake.v1.json` and the reviewed
narrative registry.

## Contract

- Input contract: announcement-style source events.
- Conversion contract:
  `src.scanners.announcement_mapping_intake.announcement_events_to_evidence_packs`.
- Source event schema: `source-event-schema-v1`.
- Output report: `announcement-mapping-intake-v1`.
- Trust policy: all mappings and evidence rows remain `candidate_untrusted`.
- Promotion policy: no writes to reviewed or trusted mapping stores.
- Quality policy: missing source URL and missing event date remain visible as
  `quality_gaps`.

## Fixture Result

The fixture acceptance run generated:

- JSON: `outputs/announcement_mapping_intake/2026-05-29-mik-56-fixture/announcement_mapping_intake_report.json`
- HTML: `outputs/announcement_mapping_intake/2026-05-29-mik-56-fixture/announcement_mapping_intake_report.html`

Fixture summary:

- Announcement events: 2
- Candidate mappings: 2
- Trusted mappings: 0
- Quality gaps: 2

The HTML report includes an `公告证据详情` section with stock, narrative, title,
supported claim types, quality gaps, and trust state for each announcement
evidence candidate.
