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
    .disclaimer {{ border-left: 4px solid #111827; padding-left: 14px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{escape(fund['fund_name'])} ({escape(fund['fund_code'])})</h1>
    <p class="meta">As of: {escape(metadata['as_of_date'])} | Data quality: {escape(metadata['data_quality'])} | Scoring model: {escape(metadata['scoring_model_version'])}</p>
  </header>

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


def _format_mapping_methods(mapping_methods: dict[str, int]) -> str:
    if not mapping_methods:
        return "none"
    return ", ".join(
        f"{method}: {count}" for method, count in sorted(mapping_methods.items())
    )
