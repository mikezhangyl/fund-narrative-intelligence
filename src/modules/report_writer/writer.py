from __future__ import annotations

import math
from html import escape
from pathlib import Path
from typing import Any

from src.modules.narrative_intelligence.model import (
    candidate_display_name,
    candidate_taxonomy_display,
)

DISCLAIMER = "本报告仅用于基金重仓叙事分析，不构成投资建议，也不构成买入、卖出或持有建议。"

_RADAR_DIMENSIONS = [
    ("earnings_score", "盈利验证", "Earnings"),
    ("capital_score", "资金强化", "Capital"),
    ("valuation_risk_score", "估值风险", "Valuation Risk"),
    ("momentum_score", "叙事动量", "Momentum"),
    ("counter_evidence_risk_score", "反向证据风险", "Counter-Evidence Risk"),
]


def write_reports(scoring_payload: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    fund_code = scoring_payload["metadata"]["fund_code"]
    markdown = render_markdown_report(scoring_payload)
    html = render_html_report(scoring_payload, markdown)

    markdown_path = output_dir / f"fund_{fund_code}_report.md"
    html_path = output_dir / f"fund_{fund_code}_report.html"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return {"markdown": markdown_path, "html": html_path}


def render_markdown_report(scoring_payload: dict[str, Any]) -> str:
    fund = scoring_payload["fund"]
    primary = scoring_payload["primary_narrative"]
    secondary = scoring_payload["secondary_narratives"]
    holdings = scoring_payload["holdings"]
    metadata = scoring_payload["metadata"]

    lines = [
        f"# {fund['fund_name']} ({fund['fund_code']})",
        "",
        f"- As of: {metadata['as_of_date']}",
        f"- Data quality: {metadata['data_quality']}",
        f"- Scoring model: {metadata['scoring_model_version']}",
        "",
        *_render_data_source_notice_lines(scoring_payload),
        "",
        "## Top Holdings",
        "",
        "| Stock | Name | Weight |",
        "| --- | --- | ---: |",
    ]
    for holding in holdings:
        lines.append(
            f"| {holding['stock_code']} | {holding['stock_name']} | {holding['weight']:.2%} |"
        )

    lines.extend(
        [
            "",
            "## Mapping Coverage",
            "",
            *_render_mapping_coverage_lines(scoring_payload),
            "",
            *_render_mapping_precision_flag_lines(scoring_payload),
            "",
            *_render_mapping_rationale_lines(scoring_payload),
            "",
            *_render_excluded_mapping_candidate_lines(scoring_payload),
            "",
            *_render_candidate_narrative_lines(scoring_payload),
            "",
            *_render_mapping_proposal_lines(scoring_payload),
            "",
            *_render_candidate_generation_issue_lines(scoring_payload),
            "",
            *_render_emerging_narrative_lines(scoring_payload),
            "",
            *_render_narrative_evidence_summary_lines(scoring_payload),
            "",
            *_render_announcement_lines(scoring_payload),
            "",
            *_render_announcement_evidence_lines(scoring_payload),
            "",
            *_render_news_evidence_lines(scoring_payload),
            "",
            *_render_market_quote_lines(scoring_payload),
            "",
            *_render_valuation_snapshot_lines(scoring_payload),
            "",
            *_render_financial_metrics_lines(scoring_payload),
            "",
            "## Primary Narrative",
            "",
            _render_narrative_markdown(primary)
            if primary
            else "No mapped narrative exposure. The current registry and stock mapping fixtures do not yet cover this fund's holdings.",
            "",
            "## Secondary Narratives",
            "",
        ]
    )
    for narrative in secondary:
        lines.extend([_render_narrative_markdown(narrative), ""])

    lines.extend(
        [
            "## Supporting Evidence",
            "",
            *_render_evidence_lines(scoring_payload["supporting_evidence"]),
            "",
            "## Risk Evidence",
            "",
            *_render_evidence_lines(scoring_payload["risk_evidence"]),
            "",
            "## Disclaimer",
            "",
            DISCLAIMER,
            "",
        ]
    )
    return "\n".join(lines)


def render_html_report(scoring_payload: dict[str, Any], markdown: str | None = None) -> str:
    del markdown
    fund = scoring_payload["fund"]
    metadata = scoring_payload["metadata"]
    title = escape(
        f"{scoring_payload['fund']['fund_name']} ({scoring_payload['fund']['fund_code']})"
    )
    holdings_rows = "\n".join(
        "<tr>"
        f"<td>{escape(holding['stock_code'])}</td>"
        f"<td>{escape(holding['stock_name'])}</td>"
        f"<td>{holding['weight']:.2%}</td>"
        "</tr>"
        for holding in scoring_payload["holdings"]
    )
    primary = scoring_payload["primary_narrative"]
    secondary = scoring_payload["secondary_narratives"]
    secondary_html = "\n".join(_render_narrative_html(item) for item in secondary)
    data_source_notice_html = _render_data_source_notice_html(scoring_payload)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; line-height: 1.6; color: #1f2937; background: #f8fafc; }}
    main {{ max-width: 1080px; margin: 0 auto; background: #fff; border: 1px solid #e5e7eb; padding: 36px; }}
    h1, h2, h3 {{ color: #111827; }}
    section {{ border-top: 1px solid #e5e7eb; padding-top: 20px; margin-top: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    .meta, .narrative-meta {{ color: #4b5563; }}
    .data-source-notice {{ background: #fff7ed; border: 1px solid #fed7aa; padding: 16px; }}
    .data-source-notice p {{ margin: 8px 0; }}
    .disclaimer {{ border-left: 4px solid #111827; padding-left: 14px; }}
    .radar-layout {{ display: grid; grid-template-columns: minmax(280px, 360px) 1fr; gap: 20px; align-items: center; margin: 16px 0; }}
    .radar-chart svg {{ display: block; width: 100%; height: auto; }}
    .radar-grid {{ fill: none; stroke: #d1d5db; stroke-width: 1; }}
    .radar-axis {{ stroke: #cbd5e1; stroke-width: 1; }}
    .radar-area {{ fill: rgba(29, 78, 216, 0.18); stroke: #1d4ed8; stroke-width: 2; }}
    .radar-point {{ fill: #1d4ed8; stroke: #fff; stroke-width: 1.5; }}
    .radar-label {{ fill: #111827; font-size: 12px; font-weight: 600; }}
    .radar-score {{ fill: #6b7280; font-size: 11px; }}
    .radar-note {{ color: #4b5563; margin: 0 0 12px; }}
    .axis-list {{ display: grid; gap: 8px; }}
    .axis-item {{ display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px dashed #e5e7eb; padding-bottom: 6px; }}
    .axis-value {{ color: #1d4ed8; font-weight: 700; }}
    @media (max-width: 900px) {{ .radar-layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{escape(fund['fund_name'])} ({escape(fund['fund_code'])})</h1>
    <p class="meta">As of: {escape(metadata['as_of_date'])} | Data quality: {escape(metadata['data_quality'])} | Scoring model: {escape(metadata['scoring_model_version'])}</p>
  </header>

  {data_source_notice_html}

  <section class="holdings">
    <h2>Top Holdings</h2>
    <table>
      <thead><tr><th>Stock</th><th>Name</th><th>Weight</th></tr></thead>
      <tbody>
        {holdings_rows}
      </tbody>
    </table>
  </section>

  <section class="mapping-coverage">
    <h2>Mapping Coverage</h2>
    {_render_mapping_coverage_html(scoring_payload)}
  </section>

  {_render_mapping_precision_flags_html(scoring_payload)}

  {_render_mapping_rationales_html(scoring_payload)}

  {_render_excluded_mapping_candidates_html(scoring_payload)}

  {_render_candidate_narratives_html(scoring_payload)}

  {_render_mapping_proposals_html(scoring_payload)}

  {_render_candidate_generation_issues_html(scoring_payload)}

  {_render_emerging_narratives_html(scoring_payload)}

  {_render_narrative_evidence_summary_html(scoring_payload)}

  {_render_announcements_html(scoring_payload)}

  {_render_announcement_evidence_html(scoring_payload)}

  {_render_news_evidence_html(scoring_payload)}

  {_render_market_quotes_html(scoring_payload)}

  {_render_valuation_snapshots_html(scoring_payload)}

  {_render_financial_metrics_html(scoring_payload)}

  <section class="primary-narrative">
    <h2>Primary Narrative</h2>
    {_render_narrative_html(primary) if primary else "<p>No mapped narrative exposure. The current registry and stock mapping fixtures do not yet cover this fund's holdings.</p>"}
  </section>

  <section class="secondary-narratives">
    <h2>Secondary Narratives</h2>
    {secondary_html if secondary_html else "<p>No secondary narratives in the current mapping output.</p>"}
  </section>

  <section class="supporting-evidence">
    <h2>Supporting Evidence</h2>
    {_render_evidence_html(scoring_payload["supporting_evidence"])}
  </section>

  <section class="risk-evidence">
    <h2>Risk Evidence</h2>
    {_render_evidence_html(scoring_payload["risk_evidence"])}
  </section>

  <section class="disclaimer">
    <h2>Disclaimer</h2>
    <p>{escape(DISCLAIMER)}</p>
  </section>
</main>
</body>
</html>
"""


def _render_data_source_notice_lines(scoring_payload: dict[str, Any]) -> list[str]:
    foundation = _provider_foundation(scoring_payload)
    if not foundation["disclosure_required"]:
        return []

    lines = [
        "## Data Source Notice",
        "",
        f"> {foundation['disclosure_message']}",
        "",
        "| Layer | Provider | Quality | Mock | Source | Note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for layer in foundation["layers"].values():
        source = layer.get("source_url") or "-"
        mock_label = "yes" if layer["is_mock"] else "no"
        note = layer.get("note") or "-"
        lines.append(
            f"| {_layer_display_name(layer)} | {layer['provider_name']} | "
            f"{layer['data_quality']} | {mock_label} | {source} | {note} |"
        )

    degradation_events = foundation.get("degradation_events", [])
    if degradation_events:
        lines.extend(["", "### Degradation Events", ""])
        for event in degradation_events:
            reason = event.get("reason", "")
            event_type = event.get("type", "unknown")
            fallback = event.get("fallback_provider_mode")
            suffix = f" fallback={fallback}" if fallback else ""
            lines.append(f"- `{event_type}`{suffix}: {reason}")
    return lines


def _render_data_source_notice_html(scoring_payload: dict[str, Any]) -> str:
    foundation = _provider_foundation(scoring_payload)
    if not foundation["disclosure_required"]:
        return ""

    layer_rows = "\n".join(
        "<tr>"
        f"<td>{escape(_layer_display_name(layer))}</td>"
        f"<td>{escape(layer['provider_name'])}</td>"
        f"<td>{escape(layer['data_quality'])}</td>"
        f"<td>{'yes' if layer['is_mock'] else 'no'}</td>"
        f"<td>{escape(str(layer.get('source_url') or '-'))}</td>"
        f"<td>{escape(str(layer.get('note') or '-'))}</td>"
        "</tr>"
        for layer in foundation["layers"].values()
    )
    degradation_events = foundation.get("degradation_events", [])
    if degradation_events:
        event_items = "\n".join(
            "<li>"
            f"<code>{escape(event.get('type', 'unknown'))}</code>"
            f"{' fallback=' + escape(event['fallback_provider_mode']) if event.get('fallback_provider_mode') else ''}: "
            f"{escape(event.get('reason', ''))}"
            "</li>"
            for event in degradation_events
        )
        degradation_html = f"<h3>Degradation Events</h3><ul>{event_items}</ul>"
    else:
        degradation_html = ""
    return f"""
  <section class="data-source-notice">
    <h2>Data Source Notice</h2>
    <p>{escape(foundation['disclosure_message'])}</p>
    <table>
      <thead><tr><th>Layer</th><th>Provider</th><th>Quality</th><th>Mock</th><th>Source</th><th>Note</th></tr></thead>
      <tbody>{layer_rows}</tbody>
    </table>
    {degradation_html}
  </section>
"""


def _provider_foundation(scoring_payload: dict[str, Any]) -> dict[str, Any]:
    foundation = scoring_payload.get("provider_foundation")
    if foundation:
        return foundation

    data_quality = scoring_payload.get("metadata", {}).get("data_quality", "mock")
    disclosure_required = data_quality != "fresh"
    return {
        "effective_data_quality": data_quality,
        "disclosure_required": disclosure_required,
        "disclosure_message": (
            "Mock 数据：本报告使用 V1 Mock fixtures，不代表完整真实环境输出。"
            if disclosure_required
            else "数据源为真实 provider，但仍仅用于叙事分析，不构成投资建议。"
        ),
        "layers": {},
        "degradation_events": scoring_payload.get("degradation_events", []),
    }


def _layer_display_name(layer: dict[str, Any]) -> str:
    return str(layer.get("display_name") or layer.get("layer") or "unknown")


def _narrative_title(narrative: dict[str, Any]) -> str:
    return str(
        narrative.get("display_name")
        or narrative.get("canonical_name_zh")
        or narrative.get("name")
        or narrative.get("narrative_id")
        or "Unknown Narrative"
    )


def _render_narrative_markdown(narrative: dict[str, Any]) -> str:
    state = narrative["state"]
    dimensions = state["dimensions"]
    interpretation = narrative.get("interpretation", {})
    lines = [
        f"### {_narrative_title(narrative)}",
        "",
        f"- Narrative ID: `{narrative['narrative_id']}`",
        f"- Exposure: {narrative['normalized_exposure']:.1%} of mapped narrative exposure",
        f"- Lifecycle stage: `{state['stage']}`",
        f"- Sustainability score: {state['sustainability_score']}",
        f"- Confidence: {state['confidence']:.2f}",
        f"- Data quality: `{state['data_quality']}`",
        "",
        "#### Interpretation",
        "",
        f"- {interpretation.get('stage_explanation', 'No interpretation available.')}",
        f"- {interpretation.get('risk_explanation', 'No risk interpretation available.')}",
        f"- {interpretation.get('confidence_note', 'No confidence note available.')}",
        "",
        "| Dimension | Score | Confidence |",
        "| --- | ---: | ---: |",
    ]
    for name, dimension in dimensions.items():
        lines.append(
            f"| {name} | {dimension['score']} | {dimension['confidence']:.2f} |"
        )
    return "\n".join(lines)


def _render_evidence_lines(evidence_items: list[dict[str, Any]]) -> list[str]:
    if not evidence_items:
        return ["- No evidence available in V1 fixtures."]
    return [
        f"- **{item['title']}** ({item['source']}, {item['event_date']}): {item['summary']}"
        for item in evidence_items
    ]


def _render_mapping_coverage_lines(scoring_payload: dict[str, Any]) -> list[str]:
    coverage = scoring_payload.get("mapping_coverage")
    if not coverage:
        return ["- Mapping coverage was not computed."]

    lines = [
        f"- Coverage ratio: {coverage['coverage_ratio']:.1%}",
        f"- Covered holdings: {coverage['covered_holding_count']} / {coverage['total_holding_count']}",
        f"- Covered weight: {coverage['covered_weight']:.2%} / {coverage['total_weight']:.2%}",
        f"- Mapping methods: {_format_mapping_methods(coverage.get('mapping_methods', {}))}",
    ]
    unmapped_holdings = scoring_payload.get("unmapped_holdings", [])
    if unmapped_holdings:
        lines.append(
            "- Unmapped holdings: "
            + ", ".join(
                f"{holding['stock_code']} {holding['stock_name']}"
                for holding in unmapped_holdings
            )
        )
    return lines


def _render_mapping_precision_flag_lines(
    scoring_payload: dict[str, Any],
) -> list[str]:
    flags = scoring_payload.get("mapping_precision_flags", [])
    if not flags:
        return []

    lines = [
        "## Mapping Precision Flags",
        "",
        "| Stock | Name | Flag | Narratives | Confidence | Action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for flag in flags:
        lines.append(
            "| "
            f"{flag.get('stock_code') or '-'} | "
            f"{flag.get('stock_name') or '-'} | "
            f"{flag.get('type') or '-'} | "
            f"{', '.join(flag.get('narratives', [])) or '-'} | "
            f"{flag.get('confidence_before'):.2f} -> "
            f"{flag.get('confidence_after'):.2f} | "
            f"{_format_precision_action(flag.get('recommended_action'))} |"
        )
    return lines


def _render_mapping_rationale_lines(scoring_payload: dict[str, Any]) -> list[str]:
    rationales = scoring_payload.get("mapping_rationales", [])
    if not rationales:
        return []

    lines = [
        "## Mapping Rationales",
        "",
        "| Stock | Name | Narrative | Method | Confidence | Terms | Review | Reason |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for rationale in rationales:
        terms = ", ".join(rationale.get("matched_terms", [])) or "-"
        review_label = "needs review" if rationale.get("needs_review") else "-"
        lines.append(
            "| "
            f"{rationale.get('stock_code') or '-'} | "
            f"{rationale.get('stock_name') or '-'} | "
            f"{rationale.get('narrative_name') or rationale.get('narrative_id') or '-'} | "
            f"{rationale.get('method') or '-'} | "
            f"{float(rationale.get('confidence', 0)):.2f} | "
            f"{terms} | "
            f"{review_label} | "
            f"{rationale.get('reason') or '-'} |"
        )
    return lines


def _render_excluded_mapping_candidate_lines(
    scoring_payload: dict[str, Any],
) -> list[str]:
    candidates = scoring_payload.get("excluded_mapping_candidates", [])
    if not candidates:
        return []

    lines = [
        "## Excluded Mapping Candidates",
        "",
        "| Stock | Name | Candidate Narrative | Method | Terms | Action | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in candidates:
        terms = ", ".join(candidate.get("matched_terms", [])) or "-"
        lines.append(
            "| "
            f"{candidate.get('stock_code') or '-'} | "
            f"{candidate.get('stock_name') or '-'} | "
            f"{candidate.get('narrative_name') or candidate.get('narrative_id') or '-'} | "
            f"{candidate.get('method') or '-'} | "
            f"{terms} | "
            f"{candidate.get('recommended_action') or '-'} | "
            f"{candidate.get('reason') or '-'} |"
        )
    return lines


def _render_candidate_narrative_lines(
    scoring_payload: dict[str, Any],
) -> list[str]:
    candidates = scoring_payload.get("candidate_narratives", [])
    if not candidates:
        return []

    lines = [
        "## Candidate Narratives For Review",
        "",
        "| Candidate | Taxonomy | Status | Triggering Stocks | Related Exclusions | Definition | Citations | Rationale |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in candidates:
        citation_count = len(candidate.get("representative_citations", []))
        lines.append(
            "| "
            f"{candidate_display_name(candidate, candidate.get('candidate_narrative_id') or '-')} | "
            f"{candidate_taxonomy_display(candidate, '-')} | "
            f"{candidate.get('human_review_status') or candidate.get('status') or '-'} | "
            f"{', '.join(candidate.get('triggering_stock_codes', [])) or '-'} | "
            f"{', '.join(candidate.get('related_exclusion_ids', [])) or '-'} | "
            f"{candidate.get('definition_zh') or candidate.get('definition') or '-'} | "
            f"{citation_count} | "
            f"{candidate.get('rationale') or '-'} |"
        )
    return lines


def _render_mapping_proposal_lines(scoring_payload: dict[str, Any]) -> list[str]:
    payload = scoring_payload.get("mapping_proposals") or {}
    proposals = payload.get("items") or []
    if not proposals:
        return []

    lines = [
        "## Candidate Mapping Proposals",
        "",
        "| Stock | Candidate | Confidence | Source Items | Rationale |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for proposal in proposals:
        lines.append(
            "| "
            f"{proposal.get('stock_code') or '-'} {proposal.get('stock_name') or ''} | "
            f"{proposal.get('candidate_name') or proposal.get('candidate_narrative_id') or '-'} | "
            f"{_format_number_metric(proposal.get('confidence'))} | "
            f"{len(proposal.get('supporting_source_item_ids', []))} | "
            f"{proposal.get('rationale') or '-'} |"
        )
    return lines


def _render_candidate_generation_issue_lines(scoring_payload: dict[str, Any]) -> list[str]:
    failures = scoring_payload.get("candidate_generation_failures") or []
    if not failures:
        return []

    lines = [
        "## Narrative Generation Issues",
        "",
        "Some candidate seeds could not be curated by the configured external model after retries. These failures are shown explicitly and are not replaced with deterministic fallback output.",
        "",
        "| Seed | Provider | Model | Attempts | Stocks | Reason |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for failure in failures:
        lines.append(
            "| "
            f"{failure.get('seed_id') or '-'} | "
            f"{failure.get('provider_name') or '-'} | "
            f"{failure.get('model') or '-'} | "
            f"{failure.get('attempt_count') or 0} | "
            f"{', '.join(failure.get('triggering_stock_codes', [])) or '-'} | "
            f"{failure.get('reason') or '-'} |"
        )
    return lines


def _render_emerging_narrative_lines(scoring_payload: dict[str, Any]) -> list[str]:
    candidates = scoring_payload.get("generated_candidate_narratives", [])
    fund_tags = [
        tag
        for tag in scoring_payload.get("fund_exposure_tags", [])
        if not (tag.get("linked_narrative_ids") or [])
    ]
    if not candidates and not fund_tags:
        return []

    lines = [
        "## Emerging Narrative Signals",
        "",
        "These are preview-only signals derived from cross-holding tags and generated candidates. They do not yet change active scoring.",
        "",
    ]
    if candidates:
        lines.extend(
            [
                "### Generated Candidates",
                "",
                "| Candidate | Taxonomy | Triggering Stocks | Confidence | Why Not Company Event |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for candidate in candidates:
            lines.append(
                "| "
                f"{candidate_display_name(candidate, candidate.get('candidate_narrative_id') or '-')} | "
                f"{candidate_taxonomy_display(candidate, '-')} | "
                f"{', '.join(candidate.get('triggering_stock_codes', [])) or '-'} | "
                f"{_format_number_metric(candidate.get('confidence'))} | "
                f"{candidate.get('why_not_company_event_zh') or '-'} |"
            )
    if fund_tags:
        lines.extend(
            [
                "",
                "### Unlinked Fund Exposure Tags",
                "",
                "| Tag | Exposure | Stocks | Confidence |",
                "| --- | ---: | --- | ---: |",
            ]
        )
        for tag in fund_tags:
            lines.append(
                "| "
                f"{tag.get('tag_name_zh') or tag.get('tag_name_en') or '-'} | "
                f"{tag.get('normalized_exposure', 0):.1%} | "
                f"{', '.join(tag.get('stock_codes', [])) or '-'} | "
                f"{_format_number_metric(tag.get('confidence'))} |"
            )
    return lines


def _render_candidate_generation_issues_html(scoring_payload: dict[str, Any]) -> str:
    failures = scoring_payload.get("candidate_generation_failures") or []
    if not failures:
        return ""

    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(failure.get('seed_id') or '-'))}</td>"
        f"<td>{escape(str(failure.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(failure.get('model') or '-'))}</td>"
        f"<td>{escape(str(failure.get('attempt_count') or 0))}</td>"
        f"<td>{escape(', '.join(failure.get('triggering_stock_codes', [])) or '-')}</td>"
        f"<td>{escape(str(failure.get('reason') or '-'))}</td>"
        "</tr>"
        for failure in failures
    )
    return (
        "<section class=\"candidate-generation-issues\">"
        "<h2>Narrative Generation Issues</h2>"
        "<p>Some candidate seeds could not be curated by the configured external model after retries. "
        "These failures are shown explicitly and are not replaced with deterministic fallback output.</p>"
        "<table><thead><tr><th>Seed</th><th>Provider</th><th>Model</th><th>Attempts</th><th>Stocks</th><th>Reason</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "</section>"
    )


def _render_narrative_evidence_summary_lines(
    scoring_payload: dict[str, Any],
) -> list[str]:
    payload = scoring_payload.get("narrative_evidence") or {}
    items = payload.get("items") or []
    if not items:
        return []

    lines = [
        "## Narrative Evidence Summary",
        "",
        "| Narrative | Evidence | Positive | Negative | Mixed | Status | Latest |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in items:
        lines.append(
            "| "
            f"{item.get('name') or item.get('narrative_id') or '-'} | "
            f"{item.get('evidence_count') or 0} | "
            f"{item.get('positive_count') or 0} | "
            f"{item.get('negative_count') or 0} | "
            f"{item.get('mixed_count') or 0} | "
            f"{item.get('support_status') or '-'} | "
            f"{item.get('latest_event_date') or '-'} |"
        )
    return lines


def _render_financial_metrics_lines(scoring_payload: dict[str, Any]) -> list[str]:
    metrics = _financial_metric_rows(scoring_payload)
    if not metrics:
        return []

    lines = [
        "## Financial Metrics",
        "",
        "| Stock | Report | Revenue YoY | Parent Net Profit YoY | Provider | Source |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for metric in metrics:
        lines.append(
            "| "
            f"{metric.get('stock_code') or '-'} {metric.get('stock_name') or ''} | "
            f"{_format_report_period(metric)} | "
            f"{_format_percent_metric(metric.get('revenue_yoy'))} | "
            f"{_format_percent_metric(metric.get('parent_net_profit_yoy'))} | "
            f"{metric.get('source_provider') or metric.get('provider_name') or '-'} | "
            f"{metric.get('source_url') or '-'} |"
        )
    return lines


def _render_valuation_snapshot_lines(scoring_payload: dict[str, Any]) -> list[str]:
    valuations = _valuation_snapshot_rows(scoring_payload)
    if not valuations:
        return []

    lines = [
        "## Valuation Snapshots",
        "",
        "| Stock | Basis | Price | Change | PE TTM | PB | Pressure | Provider | Source |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for valuation in valuations:
        lines.append(
            "| "
            f"{_stock_label(valuation)} | "
            f"{valuation.get('valuation_basis') or '-'} | "
            f"{_format_number_metric(valuation.get('latest_price'))} | "
            f"{_format_percent_metric(valuation.get('price_change_percent'))} | "
            f"{_format_number_metric(valuation.get('pe_ttm'))} | "
            f"{_format_number_metric(valuation.get('pb'))} | "
            f"{valuation.get('valuation_pressure') or '-'} | "
            f"{valuation.get('source_provider') or valuation.get('provider_name') or '-'} | "
            f"{valuation.get('source_url') or '-'} |"
        )
    return lines


def _render_market_quote_lines(scoring_payload: dict[str, Any]) -> list[str]:
    quotes = _market_quote_rows(scoring_payload)
    if not quotes:
        return []

    lines = [
        "## Market Quotes",
        "",
        "| Stock | Latest Price | Change | Change Amount | Previous Close | Volume | Provider | Source |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for quote in quotes:
        lines.append(
            "| "
            f"{_stock_label(quote)} | "
            f"{_format_number_metric(quote.get('latest_price'))} | "
            f"{_format_percent_metric(quote.get('change_percent'))} | "
            f"{_format_number_metric(quote.get('change_amount'))} | "
            f"{_format_number_metric(quote.get('previous_close'))} | "
            f"{_format_number_metric(quote.get('volume'))} | "
            f"{quote.get('source_provider') or quote.get('provider_name') or '-'} | "
            f"{quote.get('source_url') or '-'} |"
        )
    return lines


def _render_news_evidence_lines(scoring_payload: dict[str, Any]) -> list[str]:
    rows = _news_evidence_rows(scoring_payload)
    if not rows:
        return []

    lines = [
        "## News Evidence",
        "",
        f"- Query coverage: {_format_news_query_coverage(scoring_payload)}",
        "- Limitation: V1 classifies headline or RSS snippet text only; article bodies are not parsed.",
        "",
        "| Title | Narrative | Sentiment | Confidence | Date | Provider | Source | Reason |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.get('title') or '-'} | "
            f"{row.get('narrative_id') or '-'} | "
            f"{row.get('sentiment') or '-'} | "
            f"{_format_number_metric(row.get('confidence'))} | "
            f"{row.get('event_date') or '-'} | "
            f"{row.get('source_provider') or row.get('provider_name') or '-'} | "
            f"{row.get('source_url') or '-'} | "
            f"{row.get('classification_reason') or '-'} |"
        )
    return lines


def _render_announcement_lines(scoring_payload: dict[str, Any]) -> list[str]:
    rows = _announcement_rows(scoring_payload)
    if not rows:
        return []

    lines = [
        "## Announcements",
        "",
        "- Limitation: V1 classifies announcement metadata only; PDF content is not parsed.",
        "",
        "| Stock | Title | Category | Date | Provider | Source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{_stock_label(row)} | "
            f"{row.get('title') or '-'} | "
            f"{row.get('category') or '-'} | "
            f"{row.get('announcement_date') or row.get('event_date') or '-'} | "
            f"{row.get('source_provider') or row.get('provider_name') or '-'} | "
            f"{row.get('source_url') or '-'} |"
        )
    return lines


def _render_announcement_evidence_lines(
    scoring_payload: dict[str, Any],
) -> list[str]:
    rows = _announcement_evidence_rows(scoring_payload)
    if not rows:
        return []

    lines = [
        "## Announcement Evidence",
        "",
        "| Title | Narrative | Type | Confidence | Date | Provider | Source | Summary |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.get('title') or '-'} | "
            f"{row.get('narrative_id') or '-'} | "
            f"{row.get('type') or '-'} | "
            f"{_format_number_metric(row.get('confidence'))} | "
            f"{row.get('event_date') or '-'} | "
            f"{row.get('source_provider') or row.get('provider_name') or '-'} | "
            f"{row.get('source_url') or '-'} | "
            f"{row.get('summary') or '-'} |"
        )
    return lines


def _render_narrative_html(narrative: dict[str, Any]) -> str:
    state = narrative["state"]
    interpretation = narrative.get("interpretation", {})
    radar_chart = _render_radar_chart_html(state)
    dimension_rows = "\n".join(
        "<tr>"
        f"<td>{escape(name)}</td>"
        f"<td>{dimension['score']}</td>"
        f"<td>{dimension['confidence']:.2f}</td>"
        "</tr>"
        for name, dimension in state["dimensions"].items()
    )
    return f"""
<article class="narrative">
  <h3>{escape(_narrative_title(narrative))}</h3>
  <p class="narrative-meta">Narrative ID: {escape(narrative['narrative_id'])} | Exposure: {narrative['normalized_exposure']:.1%}</p>
  <p>Lifecycle stage: <strong>{escape(state['stage'])}</strong> | Sustainability score: {state['sustainability_score']} | Confidence: {state['confidence']:.2f}</p>
  <div class="interpretation">
    <h4>Interpretation</h4>
    <ul>
      <li>{escape(interpretation.get('stage_explanation', 'No interpretation available.'))}</li>
      <li>{escape(interpretation.get('risk_explanation', 'No risk interpretation available.'))}</li>
      <li>{escape(interpretation.get('confidence_note', 'No confidence note available.'))}</li>
    </ul>
  </div>
  {radar_chart}
  <table>
    <thead><tr><th>Dimension</th><th>Score</th><th>Confidence</th></tr></thead>
    <tbody>{dimension_rows}</tbody>
  </table>
</article>
"""


def _render_radar_chart_html(state: dict[str, Any]) -> str:
    dimensions = state.get("dimensions")
    if not isinstance(dimensions, dict) or not dimensions:
        return ""
    scores = [_radar_dimension_score(dimensions, key) for key, _, _ in _RADAR_DIMENSIONS]
    axis_items = "\n".join(
        (
            '<div class="axis-item">'
            f"<span>{escape(label_zh)} / {escape(label_en)}</span>"
            f'<span class="axis-value">{score:.0f}</span>'
            "</div>"
        )
        for (_, label_zh, label_en), score in zip(_RADAR_DIMENSIONS, scores, strict=True)
    )
    return f"""
  <section class="narrative-radar">
    <h4>五维雷达图 / Five-Dimension Radar</h4>
    <div class="radar-layout">
      <div class="radar-chart">{_radar_svg(scores)}</div>
      <div>
        <p class="radar-note">雷达图展示评分模型的五个原始维度。估值风险和反向证据风险是风险轴，分数越高代表风险越强，不代表更好。</p>
        <div class="axis-list">{axis_items}</div>
      </div>
    </div>
  </section>
"""


def _radar_svg(scores: list[float]) -> str:
    center_x = 165.0
    center_y = 145.0
    radius = 88.0
    grid_polygons = []
    for fraction in [0.25, 0.5, 0.75, 1.0]:
        points = _radar_points([100.0 * fraction] * len(scores), center_x, center_y, radius)
        grid_polygons.append(f'<polygon class="radar-grid" points="{_radar_points_attr(points)}" />')
    axes = []
    labels = []
    for index, (_, label_zh, _) in enumerate(_RADAR_DIMENSIONS):
        angle = _radar_angle(index, len(_RADAR_DIMENSIONS))
        end_x = center_x + radius * math.cos(angle)
        end_y = center_y + radius * math.sin(angle)
        axes.append(
            f'<line class="radar-axis" x1="{center_x:.1f}" y1="{center_y:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" />'
        )
        label_x = center_x + (radius + 28.0) * math.cos(angle)
        label_y = center_y + (radius + 28.0) * math.sin(angle)
        anchor = "middle"
        if label_x > center_x + 10:
            anchor = "start"
        elif label_x < center_x - 10:
            anchor = "end"
        labels.append(
            f'<text class="radar-label" x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{escape(label_zh)}'
            f'<tspan class="radar-score" x="{label_x:.1f}" dy="14">{scores[index]:.0f}</tspan></text>'
        )
    value_points = _radar_points(scores, center_x, center_y, radius)
    points = "".join(
        f'<circle class="radar-point" cx="{x:.1f}" cy="{y:.1f}" r="3.5" />'
        for x, y in value_points
    )
    return (
        '<svg viewBox="0 0 330 290" role="img" aria-label="五维雷达图">'
        f"{''.join(grid_polygons)}"
        f"{''.join(axes)}"
        f'<polygon class="radar-area" points="{_radar_points_attr(value_points)}" />'
        f"{points}"
        f"{''.join(labels)}"
        "</svg>"
    )


def _radar_points(
    scores: list[float],
    center_x: float,
    center_y: float,
    radius: float,
) -> list[tuple[float, float]]:
    return [
        (
            center_x + radius * (max(0.0, min(100.0, score)) / 100.0) * math.cos(_radar_angle(index, len(scores))),
            center_y + radius * (max(0.0, min(100.0, score)) / 100.0) * math.sin(_radar_angle(index, len(scores))),
        )
        for index, score in enumerate(scores)
    ]


def _radar_angle(index: int, total: int) -> float:
    return -math.pi / 2 + (2 * math.pi * index / total)


def _radar_points_attr(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def _radar_dimension_score(dimensions: dict[str, Any], key: str) -> float:
    value = dimensions.get(key)
    if not isinstance(value, dict):
        return 0.0
    score = value.get("score")
    if not isinstance(score, int | float):
        return 0.0
    return float(score)


def _render_evidence_html(evidence_items: list[dict[str, Any]]) -> str:
    if not evidence_items:
        return "<p>No evidence available in V1 fixtures.</p>"
    items = "\n".join(
        "<li>"
        f"<strong>{escape(item['title'])}</strong> "
        f"({escape(item['source'])}, {escape(item['event_date'])}): "
        f"{escape(item['summary'])}"
        "</li>"
        for item in evidence_items
    )
    return f"<ul>{items}</ul>"


def _render_mapping_coverage_html(scoring_payload: dict[str, Any]) -> str:
    coverage = scoring_payload.get("mapping_coverage")
    if not coverage:
        return "<p>Mapping coverage was not computed.</p>"
    unmapped_holdings = scoring_payload.get("unmapped_holdings", [])
    unmapped_html = ""
    if unmapped_holdings:
        items = "".join(
            f"<li>{escape(holding['stock_code'])} {escape(holding['stock_name'])}</li>"
            for holding in unmapped_holdings
        )
        unmapped_html = f"<h3>Unmapped Holdings</h3><ul>{items}</ul>"
    return f"""
<p>Coverage ratio: <strong>{coverage['coverage_ratio']:.1%}</strong></p>
<p>Covered holdings: {coverage['covered_holding_count']} / {coverage['total_holding_count']}</p>
<p>Covered weight: {coverage['covered_weight']:.2%} / {coverage['total_weight']:.2%}</p>
<p>Mapping methods: {escape(_format_mapping_methods(coverage.get('mapping_methods', {})))}</p>
{unmapped_html}
"""


def _render_mapping_precision_flags_html(scoring_payload: dict[str, Any]) -> str:
    flags = scoring_payload.get("mapping_precision_flags", [])
    if not flags:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(flag.get('stock_code') or '-'))}</td>"
        f"<td>{escape(str(flag.get('stock_name') or '-'))}</td>"
        f"<td>{escape(str(flag.get('type') or '-'))}</td>"
        f"<td>{escape(', '.join(flag.get('narratives', [])) or '-')}</td>"
        f"<td>{flag.get('confidence_before'):.2f} -&gt; {flag.get('confidence_after'):.2f}</td>"
        f"<td>{escape(_format_precision_action(flag.get('recommended_action')))}</td>"
        "</tr>"
        for flag in flags
    )
    return f"""
  <section class="mapping-precision-flags">
    <h2>Mapping Precision Flags</h2>
    <p>Fallback mappings listed here are kept, but should be treated as lower-confidence and needs review.</p>
    <table>
      <thead><tr><th>Stock</th><th>Name</th><th>Flag</th><th>Narratives</th><th>Confidence</th><th>Action</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_mapping_rationales_html(scoring_payload: dict[str, Any]) -> str:
    rationales = scoring_payload.get("mapping_rationales", [])
    if not rationales:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(rationale.get('stock_code') or '-'))}</td>"
        f"<td>{escape(str(rationale.get('stock_name') or '-'))}</td>"
        f"<td>{escape(str(rationale.get('narrative_name') or rationale.get('narrative_id') or '-'))}</td>"
        f"<td>{escape(str(rationale.get('method') or '-'))}</td>"
        f"<td>{float(rationale.get('confidence', 0)):.2f}</td>"
        f"<td>{escape(', '.join(rationale.get('matched_terms', [])) or '-')}</td>"
        f"<td>{escape('needs review' if rationale.get('needs_review') else '-')}</td>"
        f"<td>{escape(str(rationale.get('reason') or '-'))}</td>"
        "</tr>"
        for rationale in rationales
    )
    return f"""
  <section class="mapping-rationales">
    <h2>Mapping Rationales</h2>
    <p>Each row explains the rule or term evidence used to assign a holding to a narrative.</p>
    <table>
      <thead><tr><th>Stock</th><th>Name</th><th>Narrative</th><th>Method</th><th>Confidence</th><th>Terms</th><th>Review</th><th>Reason</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_excluded_mapping_candidates_html(scoring_payload: dict[str, Any]) -> str:
    candidates = scoring_payload.get("excluded_mapping_candidates", [])
    if not candidates:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(candidate.get('stock_code') or '-'))}</td>"
        f"<td>{escape(str(candidate.get('stock_name') or '-'))}</td>"
        f"<td>{escape(str(candidate.get('narrative_name') or candidate.get('narrative_id') or '-'))}</td>"
        f"<td>{escape(str(candidate.get('method') or '-'))}</td>"
        f"<td>{escape(', '.join(candidate.get('matched_terms', [])) or '-')}</td>"
        f"<td>{escape(str(candidate.get('recommended_action') or '-'))}</td>"
        f"<td>{escape(str(candidate.get('reason') or '-'))}</td>"
        "</tr>"
        for candidate in candidates
    )
    return f"""
  <section class="excluded-mapping-candidates">
    <h2>Excluded Mapping Candidates</h2>
    <p>These fallback candidates were intentionally excluded from scoring and narrative aggregation.</p>
    <table>
      <thead><tr><th>Stock</th><th>Name</th><th>Candidate Narrative</th><th>Method</th><th>Terms</th><th>Action</th><th>Reason</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_candidate_narratives_html(scoring_payload: dict[str, Any]) -> str:
    candidates = scoring_payload.get("candidate_narratives", [])
    if not candidates:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(candidate_display_name(candidate, candidate.get('candidate_narrative_id') or '-'))}</td>"
        f"<td>{escape(candidate_taxonomy_display(candidate, '-'))}</td>"
        f"<td>{escape(str(candidate.get('human_review_status') or candidate.get('status') or '-'))}</td>"
        f"<td>{escape(', '.join(candidate.get('triggering_stock_codes', [])) or '-')}</td>"
        f"<td>{escape(', '.join(candidate.get('related_exclusion_ids', [])) or '-')}</td>"
        f"<td>{escape(str(candidate.get('definition_zh') or candidate.get('definition') or '-'))}</td>"
        f"<td>{len(candidate.get('representative_citations', []))}</td>"
        f"<td>{escape(str(candidate.get('rationale') or '-'))}</td>"
        "</tr>"
        for candidate in candidates
    )
    return f"""
  <section class="candidate-narratives">
    <h2>Candidate Narratives For Review</h2>
    <p>These candidate narratives are review objects only. V1 does not use them for scoring until they are promoted into the active registry.</p>
    <table>
      <thead><tr><th>Candidate</th><th>Taxonomy</th><th>Status</th><th>Triggering Stocks</th><th>Related Exclusions</th><th>Definition</th><th>Citations</th><th>Rationale</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_mapping_proposals_html(scoring_payload: dict[str, Any]) -> str:
    payload = scoring_payload.get("mapping_proposals") or {}
    proposals = payload.get("items") or []
    if not proposals:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(proposal.get('stock_code') or '-'))} {escape(str(proposal.get('stock_name') or ''))}</td>"
        f"<td>{escape(str(proposal.get('candidate_name') or proposal.get('candidate_narrative_id') or '-'))}</td>"
        f"<td>{escape(_format_number_metric(proposal.get('confidence')))}</td>"
        f"<td>{len(proposal.get('supporting_source_item_ids', []))}</td>"
        f"<td>{escape(str(proposal.get('rationale') or '-'))}</td>"
        "</tr>"
        for proposal in proposals
    )
    return f"""
  <section class="mapping-proposals">
    <h2>Candidate Mapping Proposals</h2>
    <p>These proposals remain review-time suggestions and do not enter active scoring until promoted.</p>
    <table>
      <thead><tr><th>Stock</th><th>Candidate</th><th>Confidence</th><th>Source Items</th><th>Rationale</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_emerging_narratives_html(scoring_payload: dict[str, Any]) -> str:
    candidates = scoring_payload.get("generated_candidate_narratives", [])
    fund_tags = [
        tag
        for tag in scoring_payload.get("fund_exposure_tags", [])
        if not (tag.get("linked_narrative_ids") or [])
    ]
    if not candidates and not fund_tags:
        return ""
    candidate_rows = ""
    if candidates:
        candidate_rows = "\n".join(
            "<tr>"
            f"<td>{escape(candidate_display_name(candidate, candidate.get('candidate_narrative_id') or '-'))}</td>"
            f"<td>{escape(candidate_taxonomy_display(candidate, '-'))}</td>"
            f"<td>{escape(', '.join(candidate.get('triggering_stock_codes', [])) or '-')}</td>"
            f"<td>{escape(_format_number_metric(candidate.get('confidence')))}</td>"
            f"<td>{escape(str(candidate.get('why_not_company_event_zh') or '-'))}</td>"
            "</tr>"
            for candidate in candidates
        )
        candidate_html = f"""
    <h3>Generated Candidates</h3>
    <table>
      <thead><tr><th>Candidate</th><th>Taxonomy</th><th>Triggering Stocks</th><th>Confidence</th><th>Why Not Company Event</th></tr></thead>
      <tbody>{candidate_rows}</tbody>
    </table>
"""
    else:
        candidate_html = ""
    if fund_tags:
        tag_rows = "\n".join(
            "<tr>"
            f"<td>{escape(str(tag.get('tag_name_zh') or tag.get('tag_name_en') or '-'))}</td>"
            f"<td>{tag.get('normalized_exposure', 0):.1%}</td>"
            f"<td>{escape(', '.join(tag.get('stock_codes', [])) or '-')}</td>"
            f"<td>{escape(_format_number_metric(tag.get('confidence')))}</td>"
            "</tr>"
            for tag in fund_tags
        )
        tag_html = f"""
    <h3>Unlinked Fund Exposure Tags</h3>
    <table>
      <thead><tr><th>Tag</th><th>Exposure</th><th>Stocks</th><th>Confidence</th></tr></thead>
      <tbody>{tag_rows}</tbody>
    </table>
"""
    else:
        tag_html = ""
    return f"""
  <section class="emerging-narratives">
    <h2>Emerging Narrative Signals</h2>
    <p>These are preview-only signals derived from cross-holding tags and generated candidates. They do not yet change active scoring.</p>
    {candidate_html}
    {tag_html}
  </section>
"""


def _render_narrative_evidence_summary_html(scoring_payload: dict[str, Any]) -> str:
    payload = scoring_payload.get("narrative_evidence") or {}
    items = payload.get("items") or []
    if not items:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('name') or item.get('narrative_id') or '-'))}</td>"
        f"<td>{item.get('evidence_count') or 0}</td>"
        f"<td>{item.get('positive_count') or 0}</td>"
        f"<td>{item.get('negative_count') or 0}</td>"
        f"<td>{item.get('mixed_count') or 0}</td>"
        f"<td>{escape(str(item.get('support_status') or '-'))}</td>"
        f"<td>{escape(str(item.get('latest_event_date') or '-'))}</td>"
        "</tr>"
        for item in items
    )
    return f"""
  <section class="narrative-evidence-summary">
    <h2>Narrative Evidence Summary</h2>
    <p>This summarizes whether each active narrative is corroborated, conflicting, limited, or missing evidence.</p>
    <table>
      <thead><tr><th>Narrative</th><th>Evidence</th><th>Positive</th><th>Negative</th><th>Mixed</th><th>Status</th><th>Latest</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_financial_metrics_html(scoring_payload: dict[str, Any]) -> str:
    metrics = _financial_metric_rows(scoring_payload)
    if not metrics:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(_stock_label(metric))}</td>"
        f"<td>{escape(_format_report_period(metric))}</td>"
        f"<td>{escape(_format_percent_metric(metric.get('revenue_yoy')))}</td>"
        f"<td>{escape(_format_percent_metric(metric.get('parent_net_profit_yoy')))}</td>"
        f"<td>{escape(str(metric.get('source_provider') or metric.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(metric.get('source_url') or '-'))}</td>"
        "</tr>"
        for metric in metrics
    )
    return f"""
  <section class="financial-metrics">
    <h2>Financial Metrics</h2>
    <p>Provider financial metrics used by financial-derived signals when available.</p>
    <table>
      <thead><tr><th>Stock</th><th>Report</th><th>Revenue YoY</th><th>Parent Net Profit YoY</th><th>Provider</th><th>Source</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_valuation_snapshots_html(scoring_payload: dict[str, Any]) -> str:
    valuations = _valuation_snapshot_rows(scoring_payload)
    if not valuations:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(_stock_label(valuation))}</td>"
        f"<td>{escape(str(valuation.get('valuation_basis') or '-'))}</td>"
        f"<td>{escape(_format_number_metric(valuation.get('latest_price')))}</td>"
        f"<td>{escape(_format_percent_metric(valuation.get('price_change_percent')))}</td>"
        f"<td>{escape(_format_number_metric(valuation.get('pe_ttm')))}</td>"
        f"<td>{escape(_format_number_metric(valuation.get('pb')))}</td>"
        f"<td>{escape(str(valuation.get('valuation_pressure') or '-'))}</td>"
        f"<td>{escape(str(valuation.get('source_provider') or valuation.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(valuation.get('source_url') or '-'))}</td>"
        "</tr>"
        for valuation in valuations
    )
    return f"""
  <section class="valuation-snapshots">
    <h2>Valuation Snapshots</h2>
    <p>Provider valuation context used by valuation-derived signals when available.</p>
    <table>
      <thead><tr><th>Stock</th><th>Basis</th><th>Price</th><th>Change</th><th>PE TTM</th><th>PB</th><th>Pressure</th><th>Provider</th><th>Source</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_market_quotes_html(scoring_payload: dict[str, Any]) -> str:
    quotes = _market_quote_rows(scoring_payload)
    if not quotes:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(_stock_label(quote))}</td>"
        f"<td>{escape(_format_number_metric(quote.get('latest_price')))}</td>"
        f"<td>{escape(_format_percent_metric(quote.get('change_percent')))}</td>"
        f"<td>{escape(_format_number_metric(quote.get('change_amount')))}</td>"
        f"<td>{escape(_format_number_metric(quote.get('previous_close')))}</td>"
        f"<td>{escape(_format_number_metric(quote.get('volume')))}</td>"
        f"<td>{escape(str(quote.get('source_provider') or quote.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(quote.get('source_url') or '-'))}</td>"
        "</tr>"
        for quote in quotes
    )
    return f"""
  <section class="market-quotes">
    <h2>Market Quotes</h2>
    <p>Provider quote snapshots used by market-quote-derived signals when available.</p>
    <table>
      <thead><tr><th>Stock</th><th>Latest Price</th><th>Change</th><th>Change Amount</th><th>Previous Close</th><th>Volume</th><th>Provider</th><th>Source</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_news_evidence_html(scoring_payload: dict[str, Any]) -> str:
    rows_data = _news_evidence_rows(scoring_payload)
    if not rows_data:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row.get('title') or '-'))}</td>"
        f"<td>{escape(str(row.get('narrative_id') or '-'))}</td>"
        f"<td>{escape(str(row.get('sentiment') or '-'))}</td>"
        f"<td>{escape(_format_number_metric(row.get('confidence')))}</td>"
        f"<td>{escape(str(row.get('event_date') or '-'))}</td>"
        f"<td>{escape(str(row.get('source_provider') or row.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(row.get('source_url') or '-'))}</td>"
        f"<td>{escape(str(row.get('classification_reason') or '-'))}</td>"
        "</tr>"
        for row in rows_data
    )
    return f"""
  <section class="news-evidence">
    <h2>News Evidence</h2>
    <p>Query coverage: {escape(_format_news_query_coverage(scoring_payload))}</p>
    <p>Limitation: V1 classifies headline or RSS snippet text only; article bodies are not parsed.</p>
    <table>
      <thead><tr><th>Title</th><th>Narrative</th><th>Sentiment</th><th>Confidence</th><th>Date</th><th>Provider</th><th>Source</th><th>Reason</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_announcements_html(scoring_payload: dict[str, Any]) -> str:
    rows_data = _announcement_rows(scoring_payload)
    if not rows_data:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(_stock_label(row))}</td>"
        f"<td>{escape(str(row.get('title') or '-'))}</td>"
        f"<td>{escape(str(row.get('category') or '-'))}</td>"
        f"<td>{escape(str(row.get('announcement_date') or row.get('event_date') or '-'))}</td>"
        f"<td>{escape(str(row.get('source_provider') or row.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(row.get('source_url') or '-'))}</td>"
        "</tr>"
        for row in rows_data
    )
    return f"""
  <section class="announcements">
    <h2>Announcements</h2>
    <p>Limitation: V1 classifies announcement metadata only; PDF content is not parsed.</p>
    <table>
      <thead><tr><th>Stock</th><th>Title</th><th>Category</th><th>Date</th><th>Provider</th><th>Source</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _render_announcement_evidence_html(scoring_payload: dict[str, Any]) -> str:
    rows_data = _announcement_evidence_rows(scoring_payload)
    if not rows_data:
        return ""
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row.get('title') or '-'))}</td>"
        f"<td>{escape(str(row.get('narrative_id') or '-'))}</td>"
        f"<td>{escape(str(row.get('type') or '-'))}</td>"
        f"<td>{escape(_format_number_metric(row.get('confidence')))}</td>"
        f"<td>{escape(str(row.get('event_date') or '-'))}</td>"
        f"<td>{escape(str(row.get('source_provider') or row.get('provider_name') or '-'))}</td>"
        f"<td>{escape(str(row.get('source_url') or '-'))}</td>"
        f"<td>{escape(str(row.get('summary') or '-'))}</td>"
        "</tr>"
        for row in rows_data
    )
    return f"""
  <section class="announcement-evidence">
    <h2>Announcement Evidence</h2>
    <table>
      <thead><tr><th>Title</th><th>Narrative</th><th>Type</th><th>Confidence</th><th>Date</th><th>Provider</th><th>Source</th><th>Summary</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""


def _news_evidence_rows(scoring_payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = scoring_payload.get("news_evidence")
    if not isinstance(payload, dict):
        return []
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        return []
    provider_name = payload.get("provider_name")
    return [
        {**item, "provider_name": item.get("provider_name") or provider_name}
        for item in evidence
        if isinstance(item, dict)
    ]


def _format_news_query_coverage(scoring_payload: dict[str, Any]) -> str:
    payload = scoring_payload.get("news_evidence")
    if not isinstance(payload, dict):
        return "unavailable"
    query_scope = payload.get("query_scope")
    if not isinstance(query_scope, dict):
        return "unavailable"
    requested = query_scope.get("requested_narrative_ids") or []
    queried = query_scope.get("queried_narrative_ids") or []
    omitted = query_scope.get("omitted_narrative_ids") or []
    return (
        f"queried {len(queried)}/{len(requested)} requested narratives; "
        f"omitted {len(omitted)}; query_limit={query_scope.get('query_limit', '-')}"
    )


def _announcement_rows(scoring_payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = scoring_payload.get("announcements")
    if not isinstance(payload, dict):
        return []
    rows = payload.get("announcements")
    if not isinstance(rows, list):
        return []
    provider_name = payload.get("provider_name")
    return [
        {**row, "provider_name": row.get("provider_name") or provider_name}
        for row in rows
        if isinstance(row, dict)
    ]


def _announcement_evidence_rows(
    scoring_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    payload = scoring_payload.get("announcement_evidence")
    if not isinstance(payload, dict):
        return []
    rows = payload.get("evidence")
    if not isinstance(rows, list):
        return []
    provider_name = payload.get("provider_name")
    return [
        {**row, "provider_name": row.get("provider_name") or provider_name}
        for row in rows
        if isinstance(row, dict)
    ]


def _valuation_snapshot_rows(scoring_payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = scoring_payload.get("valuation_snapshots")
    if not isinstance(payload, dict):
        return []
    valuations = payload.get("valuations")
    if not isinstance(valuations, list):
        return []
    basis = payload.get("valuation_basis")
    return [
        {**valuation, "valuation_basis": valuation.get("valuation_basis") or basis}
        for valuation in valuations
        if isinstance(valuation, dict)
    ]


def _market_quote_rows(scoring_payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = scoring_payload.get("market_quotes")
    if not isinstance(payload, dict):
        return []
    quotes = payload.get("quotes")
    if not isinstance(quotes, list):
        return []
    provider_name = payload.get("provider_name")
    source_url = payload.get("source_url")
    return [
        {
            **quote,
            "provider_name": quote.get("provider_name") or provider_name,
            "source_url": quote.get("source_url") or source_url,
        }
        for quote in quotes
        if isinstance(quote, dict)
    ]


def _financial_metric_rows(scoring_payload: dict[str, Any]) -> list[dict[str, Any]]:
    payload = scoring_payload.get("financial_metrics")
    if not isinstance(payload, dict):
        return []
    metrics = payload.get("metrics")
    if not isinstance(metrics, list):
        return []
    return [metric for metric in metrics if isinstance(metric, dict)]


def _stock_label(metric: dict[str, Any]) -> str:
    stock_code = str(metric.get("stock_code") or "-")
    stock_name = str(metric.get("stock_name") or "")
    return f"{stock_code} {stock_name}".strip()


def _format_report_period(metric: dict[str, Any]) -> str:
    report_date = metric.get("report_date") or "-"
    report_type = metric.get("report_type") or ""
    return f"{report_date} {report_type}".strip()


def _format_percent_metric(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}%"
    return "-"


def _format_number_metric(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}"
    return "-"


def _format_precision_action(action: Any) -> str:
    if action == "manual_review":
        return "needs review"
    if action == "curation_review":
        return "curation review"
    return str(action or "-")


def _format_mapping_methods(mapping_methods: dict[str, int]) -> str:
    if not mapping_methods:
        return "none"
    return ", ".join(
        f"{method}: {count}" for method, count in sorted(mapping_methods.items())
    )
