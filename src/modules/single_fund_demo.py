from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from src.modules.snapshot_writer.writer import write_json_artifact

DEMO_VERSION = "single-fund-demo-v1"


class SingleFundDemoError(ValueError):
    pass


def build_single_fund_demo_payload(
    raw: dict[str, Any],
    scoring: dict[str, Any],
    workspace_snapshot: dict[str, Any],
) -> dict[str, Any]:
    fund = _dict_value(raw.get("fund") or scoring.get("fund"), "fund")
    fund_code = str(fund.get("fund_code") or raw.get("fund_code") or "")
    as_of_date = str(
        raw.get("as_of_date")
        or scoring.get("metadata", {}).get("as_of_date")
        or workspace_snapshot.get("as_of_date")
        or ""
    )
    primary = _dict_value(scoring.get("primary_narrative"), "primary_narrative")
    state = _dict_value(primary.get("state"), "primary_narrative.state")
    registry = _registry_by_id(raw.get("narrative_registry") or [])
    holdings = _top_holding_rows(
        holdings=raw.get("holdings") or scoring.get("holdings") or [],
        mappings=raw.get("stock_narrative_mappings") or [],
        registry=registry,
        market_quotes=_by_stock(
            (raw.get("market_quotes") or {}).get("quotes")
            or (scoring.get("market_quotes") or {}).get("quotes")
            or []
        ),
        valuations=_by_stock(
            (raw.get("valuation_snapshots") or {}).get("valuations")
            or (scoring.get("valuation_snapshots") or {}).get("valuations")
            or []
        ),
        financial_metrics=_by_stock(
            (raw.get("financial_metrics") or {}).get("metrics")
            or (scoring.get("financial_metrics") or {}).get("metrics")
            or []
        ),
    )
    provider_foundation = _dict_value(
        scoring.get("provider_foundation")
        or workspace_snapshot.get("provider_foundation"),
        "provider_foundation",
    )
    payload = {
        "version": DEMO_VERSION,
        "web_ready": True,
        "fund": {
            "fund_code": fund_code,
            "fund_name": fund.get("fund_name"),
            "fund_type": fund.get("fund_type"),
            "currency": fund.get("currency"),
            "as_of_date": as_of_date,
        },
        "primary_narrative": {
            "narrative_id": primary.get("narrative_id"),
            "name": primary.get("name"),
            "stage": state.get("stage"),
            "sustainability_score": state.get("sustainability_score"),
            "confidence": primary.get("confidence"),
            "normalized_exposure": primary.get("normalized_exposure"),
            "raw_exposure": primary.get("raw_exposure"),
            "interpretation": primary.get("interpretation", {}),
            "dimensions": state.get("dimensions", {}),
        },
        "holdings": holdings,
        "mapping_coverage": raw.get("mapping_coverage")
        or scoring.get("mapping_coverage")
        or {},
        "evidence": {
            "announcements": _evidence_rows(
                (raw.get("announcement_evidence") or {}).get("evidence")
                or (scoring.get("announcement_evidence") or {}).get("evidence")
                or [],
                limit=8,
            ),
            "news": _evidence_rows(
                (raw.get("news_evidence") or {}).get("evidence")
                or (scoring.get("news_evidence") or {}).get("evidence")
                or [],
                limit=6,
            ),
            "signals": _signal_rows(
                raw.get("derived_signal_events")
                or scoring.get("derived_signal_events")
                or [],
                limit=10,
            ),
        },
        "data_status": _data_status(provider_foundation, workspace_snapshot),
        "source_artifacts": {
            "raw": f"fund_{fund_code}_raw.json",
            "scoring": f"fund_{fund_code}_scoring.json",
            "workspace_snapshot": f"fund_{fund_code}_workspace_snapshot.json",
        },
    }
    validate_single_fund_demo_payload(payload, require_real=False)
    return payload


def write_single_fund_demo_artifacts(
    raw: dict[str, Any],
    scoring: dict[str, Any],
    workspace_snapshot: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    payload = build_single_fund_demo_payload(raw, scoring, workspace_snapshot)
    fund_code = str(payload["fund"]["fund_code"])
    json_path = output_dir / f"fund_{fund_code}_demo.json"
    html_path = output_dir / f"fund_{fund_code}_demo.html"
    write_json_artifact(payload, json_path)
    html_path.write_text(render_single_fund_demo_html(payload), encoding="utf-8")
    return {"demo_json": json_path, "demo_html": html_path}


def validate_single_fund_demo_payload(
    payload: dict[str, Any],
    require_real: bool = True,
) -> None:
    if payload.get("version") != DEMO_VERSION:
        raise SingleFundDemoError("demo payload version must be single-fund-demo-v1")
    fund = _dict_value(payload.get("fund"), "fund")
    primary = _dict_value(payload.get("primary_narrative"), "primary_narrative")
    data_status = _dict_value(payload.get("data_status"), "data_status")
    holdings = payload.get("holdings")
    if not str(fund.get("fund_code") or "").isdigit():
        raise SingleFundDemoError("fund.fund_code must contain digits")
    if not primary.get("name"):
        raise SingleFundDemoError("primary_narrative.name is required")
    if not primary.get("stage"):
        raise SingleFundDemoError("primary_narrative.stage is required")
    if not isinstance(holdings, list) or len(holdings) < 10:
        raise SingleFundDemoError("demo requires at least ten holdings")
    if not all(item.get("narrative_id") for item in holdings):
        raise SingleFundDemoError("every demo holding must include a narrative_id")
    if require_real:
        if data_status.get("mock_layer_count") != 0:
            raise SingleFundDemoError("real demo cannot include mock provider layers")
        if data_status.get("unavailable_layer_count") != 0:
            raise SingleFundDemoError("real demo cannot include unavailable layers")


def render_single_fund_demo_html(payload: dict[str, Any]) -> str:
    validate_single_fund_demo_payload(payload, require_real=False)
    fund = payload["fund"]
    primary = payload["primary_narrative"]
    status = payload["data_status"]
    dimensions = primary.get("dimensions") or {}
    source_rows = "".join(_source_row(layer) for layer in status["layers"])
    holding_rows = "".join(_holding_row(row) for row in payload["holdings"])
    dimension_rows = "".join(
        _dimension_row(name, value) for name, value in dimensions.items()
    )
    announcement_rows = "".join(
        _evidence_row(row) for row in payload["evidence"]["announcements"]
    )
    news_rows = "".join(_evidence_row(row) for row in payload["evidence"]["news"])
    signal_rows = "".join(_signal_row(row) for row in payload["evidence"]["signals"])
    fallback_notice = _fallback_notice(status)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{_h(fund["fund_code"])} Narrative Demo</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #15191e;
      --muted: #5d6975;
      --line: #d8dde3;
      --paper: #fbfaf7;
      --panel: #ffffff;
      --blue: #245d8f;
      --green: #26735a;
      --red: #a23b3b;
      --amber: #8b6424;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 56px; }}
    header {{
      border-bottom: 1px solid var(--line);
      padding: 8px 0 22px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
    }}
    h1 {{ font-size: 30px; line-height: 1.18; margin: 0 0 8px; }}
    h2 {{ font-size: 18px; margin: 0 0 12px; }}
    h3 {{ font-size: 14px; margin: 0 0 10px; color: var(--muted); }}
    p {{ margin: 0; }}
    section {{ padding: 24px 0; border-bottom: 1px solid var(--line); }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ font-size: 12px; color: var(--muted); font-weight: 650; }}
    a {{ color: var(--blue); text-decoration: none; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .metric-label {{ color: var(--muted); font-size: 12px; }}
    .metric-value {{ font-size: 21px; font-weight: 720; margin-top: 4px; }}
    .stage {{ color: var(--amber); }}
    .notice {{
      margin-top: 14px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-left: 4px solid var(--blue);
      background: var(--panel);
    }}
    .danger {{ border-left-color: var(--red); }}
    .ok {{ border-left-color: var(--green); }}
    .muted {{ color: var(--muted); }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .tag {{ display: inline-block; padding: 2px 7px; border-radius: 999px; border: 1px solid var(--line); font-size: 12px; }}
    .right {{ text-align: right; }}
    @media (max-width: 860px) {{
      main {{ padding: 18px 14px 40px; }}
      header, .summary-grid, .two-col {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <p class="muted">{_h(fund.get("fund_code"))} / as of {_h(fund.get("as_of_date"))}</p>
      <h1>{_h(fund.get("fund_name"))}</h1>
      <p>Single-fund narrative demo focused on the top ten holdings.</p>
    </div>
    <div class="right">
      <p class="muted">Primary narrative</p>
      <h2>{_h(primary.get("name"))}</h2>
      <p class="stage">{_h(primary.get("stage"))}</p>
    </div>
  </header>

  <section>
    <div class="summary-grid">
      <div class="metric"><div class="metric-label">Sustainability score</div><div class="metric-value">{_fmt(primary.get("sustainability_score"))}</div></div>
      <div class="metric"><div class="metric-label">Confidence</div><div class="metric-value">{_pct(primary.get("confidence"))}</div></div>
      <div class="metric"><div class="metric-label">Narrative exposure</div><div class="metric-value">{_pct(primary.get("normalized_exposure"))}</div></div>
      <div class="metric"><div class="metric-label">Top-10 mapped weight</div><div class="metric-value">{_pct(payload["mapping_coverage"].get("covered_weight"))}</div></div>
    </div>
    <div class="notice ok">
      {_h((primary.get("interpretation") or {}).get("stage_explanation") or "")}
    </div>
    {fallback_notice}
  </section>

  <section>
    <h2>Top Holdings Narrative Map</h2>
    <table>
      <thead><tr><th>Stock</th><th>Weight</th><th>Narrative</th><th>Mapping</th><th>Price move</th><th>PE TTM</th><th>Revenue YoY</th><th>Net profit YoY</th></tr></thead>
      <tbody>{holding_rows}</tbody>
    </table>
  </section>

  <section>
    <div class="two-col">
      <div>
        <h2>Stage Drivers</h2>
        <table><thead><tr><th>Dimension</th><th>Score</th><th>Support</th><th>Risk</th><th>Confidence</th></tr></thead><tbody>{dimension_rows}</tbody></table>
      </div>
      <div>
        <h2>Data Sources</h2>
        <table><thead><tr><th>Layer</th><th>Provider</th><th>Quality</th><th>Disclosure</th></tr></thead><tbody>{source_rows}</tbody></table>
      </div>
    </div>
  </section>

  <section>
    <h2>Evidence Samples</h2>
    <div class="two-col">
      <div>
        <h3>Announcements</h3>
        <table><thead><tr><th>Date</th><th>Stock</th><th>Signal</th><th>Source</th></tr></thead><tbody>{announcement_rows}</tbody></table>
      </div>
      <div>
        <h3>News</h3>
        <table><thead><tr><th>Date</th><th>Sentiment</th><th>Title</th><th>Source</th></tr></thead><tbody>{news_rows}</tbody></table>
      </div>
    </div>
  </section>

  <section>
    <h2>Derived Signals</h2>
    <table><thead><tr><th>Date</th><th>Stock</th><th>Type</th><th>Strength</th><th>Confidence</th><th>Provider</th></tr></thead><tbody>{signal_rows}</tbody></table>
  </section>
</main>
</body>
</html>
"""


def _top_holding_rows(
    holdings: list[Any],
    mappings: list[Any],
    registry: dict[str, dict[str, Any]],
    market_quotes: dict[str, dict[str, Any]],
    valuations: dict[str, dict[str, Any]],
    financial_metrics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    mappings_by_stock = _by_stock(mappings)
    rows = []
    for holding in holdings[:10]:
        if not isinstance(holding, dict):
            continue
        stock_code = str(holding.get("stock_code") or "")
        mapping = mappings_by_stock.get(stock_code, {})
        narrative_id = str(mapping.get("narrative_id") or "")
        quote = market_quotes.get(stock_code, {})
        valuation = valuations.get(stock_code, {})
        financial = financial_metrics.get(stock_code, {})
        rows.append(
            {
                "stock_code": stock_code,
                "stock_name": holding.get("stock_name"),
                "industry": holding.get("industry"),
                "weight": holding.get("weight"),
                "holding_change": holding.get("holding_change"),
                "narrative_id": narrative_id,
                "narrative_name": registry.get(narrative_id, {}).get(
                    "name", narrative_id
                ),
                "mapping_confidence": mapping.get("confidence"),
                "mapping_method": mapping.get("method"),
                "mapping_weight": mapping.get("mapping_weight"),
                "latest_price": valuation.get("latest_price")
                or quote.get("latest_price"),
                "price_change_percent": valuation.get("price_change_percent")
                or quote.get("change_percent"),
                "pe_ttm": valuation.get("pe_ttm"),
                "pb": valuation.get("pb"),
                "valuation_pressure": valuation.get("valuation_pressure"),
                "revenue_yoy": financial.get("revenue_yoy"),
                "parent_net_profit_yoy": financial.get("parent_net_profit_yoy"),
                "gross_margin": financial.get("gross_margin"),
                "financial_report_date": financial.get("report_date"),
                "source_urls": {
                    "holding": (holding.get("provider_metadata") or {}).get(
                        "source_url"
                    ),
                    "quote": quote.get("source_url"),
                    "valuation": valuation.get("source_url"),
                    "financial": financial.get("source_url"),
                },
            }
        )
    return rows


def _data_status(
    provider_foundation: dict[str, Any],
    workspace_snapshot: dict[str, Any],
) -> dict[str, Any]:
    layers = list((provider_foundation.get("layers") or {}).values())
    data_source_notice = workspace_snapshot.get("data_source_notice") or {}
    mock_layers = [layer for layer in layers if layer.get("is_mock")]
    unavailable_layers = [
        layer for layer in layers if layer.get("data_quality") == "unavailable"
    ]
    return {
        "effective_data_quality": provider_foundation.get("effective_data_quality"),
        "disclosure_required": provider_foundation.get("disclosure_required"),
        "disclosure_message": provider_foundation.get("disclosure_message"),
        "mock_layer_count": data_source_notice.get(
            "mock_layer_count", len(mock_layers)
        ),
        "unavailable_layer_count": data_source_notice.get(
            "unavailable_layer_count", len(unavailable_layers)
        ),
        "degradation_event_count": len(provider_foundation.get("degradation_events", [])),
        "degradation_events": provider_foundation.get("degradation_events", []),
        "layers": [
            {
                "layer": layer.get("layer"),
                "display_name": layer.get("display_name"),
                "provider_name": layer.get("provider_name"),
                "data_quality": layer.get("data_quality"),
                "source_url": layer.get("source_url"),
                "is_mock": layer.get("is_mock"),
            }
            for layer in layers
        ],
    }


def _registry_by_id(registry: list[Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["narrative_id"]): item
        for item in registry
        if isinstance(item, dict) and item.get("narrative_id")
    }


def _by_stock(items: list[Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in items:
        if isinstance(item, dict) and item.get("stock_code"):
            result[str(item["stock_code"])] = item
    return result


def _evidence_rows(items: list[Any], limit: int) -> list[dict[str, Any]]:
    rows = [
        {
            "event_date": item.get("event_date"),
            "stock_code": item.get("stock_code"),
            "stock_name": item.get("stock_name"),
            "title": item.get("title"),
            "sentiment": item.get("sentiment"),
            "type": item.get("type"),
            "confidence": item.get("confidence"),
            "source": item.get("source") or item.get("source_provider"),
            "source_url": item.get("source_url"),
        }
        for item in items
        if isinstance(item, dict)
    ]
    return rows[:limit]


def _signal_rows(items: list[Any], limit: int) -> list[dict[str, Any]]:
    rows = [
        {
            "event_date": item.get("event_date"),
            "stock_code": item.get("source_stock_code"),
            "signal_type": item.get("signal_type"),
            "strength": item.get("strength"),
            "confidence": item.get("confidence"),
            "source": item.get("source"),
            "source_provider": item.get("source_provider"),
            "source_url": item.get("source_url"),
        }
        for item in items
        if isinstance(item, dict)
    ]
    return rows[:limit]


def _fallback_notice(status: dict[str, Any]) -> str:
    if status.get("mock_layer_count"):
        return (
            '<div class="notice danger">Mock data is present in this run. '
            "The future web UI must show this disclosure at the URL level.</div>"
        )
    if status.get("degradation_event_count"):
        return (
            '<div class="notice">Real providers were used, with provider fallback '
            f'events recorded: {_h(status.get("degradation_event_count"))}. '
            "This run remains non-mock, but the fallback is visible for review.</div>"
        )
    return '<div class="notice ok">All required layers are real provider layers.</div>'


def _holding_row(row: dict[str, Any]) -> str:
    stock = f'{row.get("stock_code")} {row.get("stock_name")}'
    return (
        "<tr>"
        f"<td>{_h(stock)}</td>"
        f"<td>{_pct(row.get('weight'))}</td>"
        f"<td>{_h(row.get('narrative_name'))}</td>"
        f"<td>{_h(row.get('mapping_method'))} / {_pct(row.get('mapping_confidence'))}</td>"
        f"<td>{_pct(row.get('price_change_percent'), already_percent=True)}</td>"
        f"<td>{_fmt(row.get('pe_ttm'))}</td>"
        f"<td>{_pct(row.get('revenue_yoy'), already_percent=True)}</td>"
        f"<td>{_pct(row.get('parent_net_profit_yoy'), already_percent=True)}</td>"
        "</tr>"
    )


def _dimension_row(name: str, value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return (
        "<tr>"
        f"<td>{_h(name)}</td>"
        f"<td>{_fmt(value.get('score'))}</td>"
        f"<td>{_h(value.get('supporting_signal_count'))}</td>"
        f"<td>{_h(value.get('risk_signal_count'))}</td>"
        f"<td>{_pct(value.get('confidence'))}</td>"
        "</tr>"
    )


def _source_row(layer: dict[str, Any]) -> str:
    disclosure = "mock" if layer.get("is_mock") else "real"
    source_url = str(layer.get("source_url") or "")
    provider = _h(layer.get("provider_name"))
    if source_url.startswith("http"):
        provider = f'<a href="{_h(source_url)}">{provider}</a>'
    return (
        "<tr>"
        f"<td>{_h(layer.get('display_name') or layer.get('layer'))}</td>"
        f"<td>{provider}</td>"
        f"<td><span class=\"tag\">{_h(layer.get('data_quality'))}</span></td>"
        f"<td>{_h(disclosure)}</td>"
        "</tr>"
    )


def _evidence_row(row: dict[str, Any]) -> str:
    source = _h(row.get("source") or "")
    source_url = str(row.get("source_url") or "")
    if source_url.startswith("http"):
        source = f'<a href="{_h(source_url)}">{source}</a>'
    label = row.get("title") or row.get("type") or row.get("sentiment")
    stock = " ".join(
        part for part in [str(row.get("stock_code") or ""), str(row.get("stock_name") or "")] if part
    )
    return (
        "<tr>"
        f"<td>{_h(row.get('event_date'))}</td>"
        f"<td>{_h(stock)}</td>"
        f"<td>{_h(label)}</td>"
        f"<td>{source}</td>"
        "</tr>"
    )


def _signal_row(row: dict[str, Any]) -> str:
    source = _h(row.get("source_provider") or row.get("source") or "")
    source_url = str(row.get("source_url") or "")
    if source_url.startswith("http"):
        source = f'<a href="{_h(source_url)}">{source}</a>'
    return (
        "<tr>"
        f"<td>{_h(row.get('event_date'))}</td>"
        f"<td>{_h(row.get('stock_code'))}</td>"
        f"<td>{_h(row.get('signal_type'))}</td>"
        f"<td>{_fmt(row.get('strength'))}</td>"
        f"<td>{_pct(row.get('confidence'))}</td>"
        f"<td>{source}</td>"
        "</tr>"
    )


def _dict_value(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SingleFundDemoError(f"{context} must be an object")
    return value


def _h(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _fmt(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return _h(value)


def _pct(value: Any, already_percent: bool = False) -> str:
    if not isinstance(value, int | float):
        return _h(value)
    normalized = value if already_percent else value * 100
    return f"{normalized:.1f}%"
