from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

DISCLAIMER = "本报告仅用于基金重仓叙事分析，不构成投资建议，也不构成买入、卖出或持有建议。"


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


def _render_narrative_markdown(narrative: dict[str, Any]) -> str:
    state = narrative["state"]
    dimensions = state["dimensions"]
    interpretation = narrative.get("interpretation", {})
    lines = [
        f"### {narrative['name']}",
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
        "| Candidate | Taxonomy | Status | Triggering Stocks | Related Exclusions | Rationale |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in candidates:
        lines.append(
            "| "
            f"{candidate.get('name') or candidate.get('candidate_narrative_id') or '-'} | "
            f"{candidate.get('canonical_taxonomy') or '-'} | "
            f"{candidate.get('human_review_status') or candidate.get('status') or '-'} | "
            f"{', '.join(candidate.get('triggering_stock_codes', [])) or '-'} | "
            f"{', '.join(candidate.get('related_exclusion_ids', [])) or '-'} | "
            f"{candidate.get('rationale') or '-'} |"
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
        "- Limitation: V1 classifies RSS titles/snippets only; article bodies are not parsed.",
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


def _render_narrative_html(narrative: dict[str, Any]) -> str:
    state = narrative["state"]
    interpretation = narrative.get("interpretation", {})
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
  <h3>{escape(narrative['name'])}</h3>
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
  <table>
    <thead><tr><th>Dimension</th><th>Score</th><th>Confidence</th></tr></thead>
    <tbody>{dimension_rows}</tbody>
  </table>
</article>
"""


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
        f"<td>{escape(str(candidate.get('name') or candidate.get('candidate_narrative_id') or '-'))}</td>"
        f"<td>{escape(str(candidate.get('canonical_taxonomy') or '-'))}</td>"
        f"<td>{escape(str(candidate.get('human_review_status') or candidate.get('status') or '-'))}</td>"
        f"<td>{escape(', '.join(candidate.get('triggering_stock_codes', [])) or '-')}</td>"
        f"<td>{escape(', '.join(candidate.get('related_exclusion_ids', [])) or '-')}</td>"
        f"<td>{escape(str(candidate.get('rationale') or '-'))}</td>"
        "</tr>"
        for candidate in candidates
    )
    return f"""
  <section class="candidate-narratives">
    <h2>Candidate Narratives For Review</h2>
    <p>These candidate narratives are review objects only. V1 does not use them for scoring until they are promoted into the active registry.</p>
    <table>
      <thead><tr><th>Candidate</th><th>Taxonomy</th><th>Status</th><th>Triggering Stocks</th><th>Related Exclusions</th><th>Rationale</th></tr></thead>
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
    <p>Limitation: V1 classifies RSS titles/snippets only; article bodies are not parsed.</p>
    <table>
      <thead><tr><th>Title</th><th>Narrative</th><th>Sentiment</th><th>Confidence</th><th>Date</th><th>Provider</th><th>Source</th><th>Reason</th></tr></thead>
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
