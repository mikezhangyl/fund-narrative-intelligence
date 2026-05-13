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
        "| Layer | Provider | Quality | Mock | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for layer in foundation["layers"].values():
        source = layer.get("source_url") or "-"
        mock_label = "yes" if layer["is_mock"] else "no"
        lines.append(
            f"| {_layer_display_name(layer)} | {layer['provider_name']} | "
            f"{layer['data_quality']} | {mock_label} | {source} |"
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
      <thead><tr><th>Layer</th><th>Provider</th><th>Quality</th><th>Mock</th><th>Source</th></tr></thead>
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


def _format_precision_action(action: Any) -> str:
    if action == "manual_review":
        return "needs review"
    return str(action or "-")


def _format_mapping_methods(mapping_methods: dict[str, int]) -> str:
    if not mapping_methods:
        return "none"
    return ", ".join(
        f"{method}: {count}" for method, count in sorted(mapping_methods.items())
    )
