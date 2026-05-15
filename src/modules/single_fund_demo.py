from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

from src.modules.snapshot_writer.writer import write_json_artifact

DEMO_VERSION = "single-fund-demo-v1"

NARRATIVE_ZH = {
    "Premium Baijiu Consumption": "高端白酒消费",
}
STAGE_ZH = {
    "emerging": "萌芽",
    "accelerating": "加速",
    "mature": "成熟",
    "weakening": "走弱",
    "broken": "破裂",
}
DIMENSION_ZH = {
    "earnings_score": "盈利验证",
    "capital_score": "资金强化",
    "valuation_risk_score": "估值风险强度",
    "momentum_score": "叙事动量",
    "counter_evidence_risk_score": "反向证据强度",
}
RADAR_DIMENSIONS = [
    {
        "key": "earnings_score",
        "zh": "盈利验证",
        "en": "Earnings validation",
        "help_zh": "盈利和财务数据是否支持该叙事。分数越高，盈利证据越支持叙事。",
        "help_en": "Whether earnings and financial data support the narrative. Higher means stronger earnings support.",
    },
    {
        "key": "capital_score",
        "zh": "资金强化",
        "en": "Capital reinforcement",
        "help_zh": "资金流、行情和资本市场信号是否强化该叙事。分数越高，资金支持越强。",
        "help_en": "Whether market and capital signals reinforce the narrative. Higher means stronger capital support.",
    },
    {
        "key": "valuation_risk_score",
        "zh": "估值风险强度",
        "en": "Valuation risk strength",
        "help_zh": "估值压力或拥挤程度。这里分数越高代表风险越强，不代表越好。",
        "help_en": "Valuation pressure or crowding. Higher means stronger risk here, not a better condition.",
    },
    {
        "key": "momentum_score",
        "zh": "叙事动量",
        "en": "Narrative momentum",
        "help_zh": "新闻、公告、行情等信号是否显示叙事仍有热度。分数越高，动量越强。",
        "help_en": "Whether news, announcements, and market signals show the narrative still has momentum. Higher means stronger momentum.",
    },
    {
        "key": "counter_evidence_risk_score",
        "zh": "反向证据强度",
        "en": "Counter-evidence strength",
        "help_zh": "和叙事相反的风险证据强度。这里分数越高代表反向证据越强，不代表越好。",
        "help_en": "Strength of evidence against the narrative. Higher means stronger counter-evidence here, not a better condition.",
    },
]
QUALITY_ZH = {
    "fresh": "新鲜",
    "partial": "部分",
    "mock": "Mock",
    "stale": "陈旧",
    "unavailable": "不可用",
}
DISCLOSURE_ZH = {
    "real": "真实",
    "mock": "Mock",
}
MAPPING_METHOD_ZH = {
    "reviewed_mapping": "已审核映射",
    "fixture_mapping": "Fixture 映射",
    "registry_rule": "规则映射",
}
SIGNAL_TYPE_ZH = {
    "relative_strength_down": "相对强度走弱",
    "relative_strength_up": "相对强度走强",
    "valuation_extreme": "估值偏高",
    "valuation_reset": "估值修复",
    "earnings_validation": "盈利验证",
    "earnings_risk": "盈利风险",
    "capital_reinforcement": "资金强化",
    "counter_evidence": "反向证据",
}
SOURCE_LAYER_ZH = {
    "Fund holdings": "基金持仓",
    "Narrative registry": "叙事库",
    "Stock mappings": "股票叙事映射",
    "Evidence": "证据",
    "Signals": "信号",
    "Announcements": "公告",
    "Market quotes": "行情",
    "Valuation": "估值",
    "Financial metrics": "财务指标",
    "News evidence": "新闻证据",
    "Derived signals": "衍生信号",
}


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
    radar_chart = _radar_chart(primary)
    announcement_rows = "".join(
        _evidence_row(row) for row in payload["evidence"]["announcements"]
    )
    news_rows = "".join(_evidence_row(row) for row in payload["evidence"]["news"])
    signal_rows = "".join(_signal_row(row) for row in payload["evidence"]["signals"])
    fallback_notice = _fallback_notice(status)
    narrative_label = _narrative_label(primary.get("name"))
    stage_label = _stage_label(primary.get("stage"))
    stage_explanation = _stage_explanation(primary)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>{_h(fund["fund_code"])} 基金叙事报告</title>
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
      grid-template-columns: minmax(0, 1fr) minmax(260px, auto);
      gap: 20px;
      align-items: end;
    }}
    h1 {{ font-size: 30px; line-height: 1.18; margin: 0 0 8px; }}
    h2 {{ font-size: 18px; margin: 0 0 12px; }}
    h3 {{ font-size: 14px; margin: 0 0 10px; color: var(--muted); }}
    p {{ margin: 0; }}
    .header-term {{ margin: 0; }}
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
    .radar-layout {{ align-items: center; display: grid; grid-template-columns: minmax(320px, 430px) 1fr; gap: 24px; }}
    .radar-chart svg {{ display: block; height: auto; max-width: 100%; }}
    .radar-grid {{ fill: none; stroke: var(--line); stroke-width: 1; }}
    .radar-axis {{ stroke: #b8c0c8; stroke-width: 1; }}
    .radar-area {{ fill: rgba(36, 93, 143, 0.2); stroke: var(--blue); stroke-width: 2; }}
    .radar-point {{ fill: var(--blue); stroke: #fff; stroke-width: 1.5; }}
    .radar-label {{ fill: var(--ink); font-size: 12px; font-weight: 650; }}
    .radar-score {{ fill: var(--muted); font-size: 11px; }}
    .radar-note {{ color: var(--muted); margin-top: 8px; }}
    .axis-list {{ display: grid; gap: 8px; margin-top: 12px; }}
    .axis-item {{ align-items: center; display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding: 7px 0; }}
    .axis-value {{ font-weight: 720; }}
    .tag {{ display: inline-block; padding: 2px 7px; border-radius: 999px; border: 1px solid var(--line); font-size: 12px; }}
    .right {{ min-width: 260px; text-align: right; }}
    .right .term {{ justify-content: flex-end; }}
    .term {{ display: inline-flex; align-items: center; gap: 5px; white-space: normal; }}
    .help {{ position: relative; display: inline-block; vertical-align: middle; }}
    .help summary {{
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--blue);
      cursor: pointer;
      display: inline-flex;
      font-size: 11px;
      font-weight: 750;
      height: 17px;
      justify-content: center;
      line-height: 1;
      list-style: none;
      width: 17px;
    }}
    .help summary::-webkit-details-marker {{ display: none; }}
    .help-card {{
      background: var(--ink);
      border-radius: 8px;
      box-shadow: 0 10px 28px rgba(21, 25, 30, 0.22);
      color: #fff;
      display: none;
      font-size: 12px;
      font-weight: 450;
      left: 0;
      line-height: 1.5;
      max-width: 320px;
      min-width: 250px;
      padding: 10px 12px;
      position: absolute;
      text-align: left;
      top: 23px;
      white-space: normal;
      z-index: 20;
    }}
    .right .help-card {{ left: auto; right: 0; }}
    .help[open] .help-card,
    .help:hover .help-card,
    .help:focus-within .help-card {{ display: block; }}
    .language-switch {{ display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 16px; }}
    .language-switch button {{
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 999px;
      color: var(--muted);
      cursor: pointer;
      font: inherit;
      padding: 5px 12px;
    }}
    html[lang="zh-CN"] button[data-lang="zh-CN"],
    html[lang="en"] button[data-lang="en"] {{
      border-color: var(--blue);
      color: var(--blue);
      font-weight: 650;
    }}
    html[lang="zh-CN"] .lang-en {{ display: none; }}
    html[lang="en"] .lang-zh {{ display: none; }}
    @media (max-width: 860px) {{
      main {{ padding: 18px 14px 40px; }}
      header, .summary-grid, .two-col, .radar-layout {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
      .language-switch {{ justify-content: flex-start; }}
      .help-card {{ max-width: min(320px, calc(100vw - 48px)); }}
    }}
  </style>
</head>
<body>
<main>
  <div class="language-switch" aria-label="Language switch">
    <button type="button" data-lang="zh-CN">中文</button>
    <button type="button" data-lang="en">English</button>
  </div>
  <header>
    <div>
      <p class="muted">{_h(fund.get("fund_code"))} / {_bi("截至", "as of")} {_h(fund.get("as_of_date"))}</p>
      <h1>{_h(fund.get("fund_name"))}</h1>
      <p>{_bi("单基金叙事报告，聚焦十大重仓股。", "Single-fund narrative demo focused on the top ten holdings.")}</p>
    </div>
    <div class="right">
      <div class="muted header-term">{_term("主叙事", "Primary narrative", "基金十大重仓聚合后暴露最高的叙事主题。这里的叙事来自本地已审核叙事库，不是本次实时自动发现。", "The dominant theme after aggregating the fund's top holdings. This narrative comes from the reviewed local registry, not live auto-discovery in this run.")}</div>
      <h2>{narrative_label}</h2>
      <div class="stage header-term">{_term("阶段", "Stage", "系统根据支持信号、风险信号、估值压力、动量和反向证据把叙事归入当前阶段。", "The system assigns the current stage from support signals, risk signals, valuation pressure, momentum, and counter-evidence.")}: {stage_label}</div>
    </div>
  </header>

  <section>
    <div class="summary-grid">
      <div class="metric"><div class="metric-label">{_term("持续性评分", "Sustainability score", "0-100 的综合评分，来自盈利验证、资金强化、估值压力、叙事动量、反向证据风险五个维度。分数越高，当前证据对叙事越友好；它不是买卖建议。", "A 0-100 composite score from earnings validation, capital reinforcement, valuation pressure, momentum, and counter-evidence risk. Higher means the current evidence is more supportive; it is not investment advice.")}</div><div class="metric-value">{_fmt(primary.get("sustainability_score"))}</div></div>
      <div class="metric"><div class="metric-label">{_term("置信度", "Confidence", "表示系统对当前叙事判断的把握程度，受数据质量、证据密度、映射置信度影响。它不是收益概率。", "How much confidence the system has in this narrative read, driven by data quality, evidence density, and mapping confidence. It is not a return probability.")}</div><div class="metric-value">{_pct(primary.get("confidence"))}</div></div>
      <div class="metric"><div class="metric-label">{_term("叙事暴露", "Narrative exposure", "十大重仓中映射到该主叙事的归一化暴露。100% 表示已映射的重仓主要集中在同一叙事上。", "Normalized exposure of the top holdings mapped to the primary narrative. 100% means the mapped top holdings are concentrated in this narrative.")}</div><div class="metric-value">{_pct(primary.get("normalized_exposure"))}</div></div>
      <div class="metric"><div class="metric-label">{_term("十大重仓映射权重", "Top-10 mapped weight", "十大重仓中已经找到叙事映射的实际持仓权重合计。这个数低时，说明还有较多重仓没有被叙事库覆盖。", "The actual portfolio weight in the top holdings that has a narrative mapping. A low value means many top holdings are not covered by the narrative registry yet.")}</div><div class="metric-value">{_pct(payload["mapping_coverage"].get("covered_weight"))}</div></div>
    </div>
    <div class="notice ok">
      {stage_explanation}
    </div>
    {fallback_notice}
  </section>

  <section>
    <h2>{_bi("十大重仓叙事映射", "Top Holdings Narrative Map")}</h2>
    <table>
      <thead><tr><th>{_bi("股票", "Stock")}</th><th>{_bi("权重", "Weight")}</th><th>{_term("叙事", "Narrative", "股票被归入的已审核叙事主题。V1 使用 reviewed mapping，不代表叙事是实时自动生成。", "The reviewed narrative theme assigned to the stock. V1 uses reviewed mappings; this does not mean the narrative was generated live.")}</th><th>{_term("映射", "Mapping", "显示映射来源和置信度。已审核映射表示来自本地人工审核映射库。", "Shows the mapping source and confidence. Reviewed mapping means it comes from the local human-reviewed mapping store.")}</th><th>{_term("价格变动", "Price move", "本次行情 provider 返回的最新价格相对前收盘价变化。若发生 fallback，页面会单独披露。", "Latest provider price change versus previous close. If a provider fallback occurred, the page discloses it separately.")}</th><th>{_term("市盈率 TTM", "PE TTM", "Eastmoney 估值接口返回的滚动市盈率，用作估值压力参考。", "Trailing PE returned by the Eastmoney valuation endpoint, used as valuation-pressure context.")}</th><th>{_term("营收同比", "Revenue YoY", "最近一期财务指标中的营业收入同比增速。", "Revenue year-over-year growth from the latest available financial metrics.")}</th><th>{_term("归母净利同比", "Net profit YoY", "最近一期财务指标中的归母净利润同比增速。", "Parent net profit year-over-year growth from the latest available financial metrics.")}</th></tr></thead>
      <tbody>{holding_rows}</tbody>
    </table>
  </section>

  {radar_chart}

  <section>
    <div class="two-col">
      <div>
        <h2>{_bi("阶段驱动因素", "Stage Drivers")}</h2>
        <table><thead><tr><th>{_term("维度", "Dimension", "评分模型拆分出的叙事判断维度。每个维度会统计对应的支持信号和风险信号。", "Narrative scoring dimensions. Each dimension counts supporting and risk signals relevant to that dimension.")}</th><th>{_term("分数", "Score", "该维度的 0-100 分。分数越高，表示该维度越支持叙事持续。", "0-100 score for this dimension. Higher means this dimension is more supportive of narrative sustainability.")}</th><th>{_term("支持信号", "Support", "推动该维度评分上升的信号数量。", "Number of signals pushing this dimension upward.")}</th><th>{_term("风险信号", "Risk", "拖累该维度评分或增加风险的信号数量。", "Number of signals weighing on this dimension or increasing risk.")}</th><th>{_term("置信度", "Confidence", "该维度判断的把握程度，受信号强度、来源和数据质量影响。", "Confidence in this dimension's read, affected by signal strength, source, and data quality.")}</th></tr></thead><tbody>{dimension_rows}</tbody></table>
      </div>
      <div>
        <h2>{_bi("数据来源", "Data Sources")}</h2>
        <table><thead><tr><th>{_term("数据层", "Layer", "报告使用的数据类别，例如持仓、估值、财务、公告、新闻和映射库。", "The data category used by the report, such as holdings, valuation, financials, announcements, news, and mapping stores.")}</th><th>{_term("Provider", "Provider", "提供该数据层的来源或适配器。URL 可点击时指向对应 provider 查询地址或来源。", "The source or adapter for this data layer. Clickable URLs point to the provider query or source when available.")}</th><th>{_term("质量", "Quality", "新鲜：本次运行从真实 provider 成功获取；部分：数据可用但覆盖、来源或完整性有限；Mock：fixture 或模拟数据；陈旧：不是本次最新获取；不可用：该层未拿到可用数据。", "Fresh: fetched successfully from a real provider in this run. Partial: usable but limited by coverage, source, or completeness. Mock: fixture or simulated data. Stale: not freshly fetched in this run. Unavailable: no usable data was returned.")}</th><th>{_term("披露", "Disclosure", "标记该层是真实 provider 数据还是 Mock 数据。只要出现 Mock 或不可用，页面必须提示用户。", "Marks whether this layer is real provider data or mock data. Any mock or unavailable layer must be disclosed to the user.")}</th></tr></thead><tbody>{source_rows}</tbody></table>
      </div>
    </div>
  </section>

  <section>
    <h2>{_bi("证据样本", "Evidence Samples")}</h2>
    <div class="two-col">
      <div>
        <h3>{_bi("公告", "Announcements")}</h3>
        <table><thead><tr><th>{_bi("日期", "Date")}</th><th>{_bi("股票", "Stock")}</th><th>{_bi("信号", "Signal")}</th><th>{_bi("来源", "Source")}</th></tr></thead><tbody>{announcement_rows}</tbody></table>
      </div>
      <div>
        <h3>{_bi("新闻", "News")}</h3>
        <table><thead><tr><th>{_bi("日期", "Date")}</th><th>{_bi("情绪", "Sentiment")}</th><th>{_bi("标题", "Title")}</th><th>{_bi("来源", "Source")}</th></tr></thead><tbody>{news_rows}</tbody></table>
      </div>
    </div>
  </section>

  <section>
    <h2>{_bi("衍生信号", "Derived Signals")}</h2>
    <table><thead><tr><th>{_bi("日期", "Date")}</th><th>{_bi("股票", "Stock")}</th><th>{_bi("类型", "Type")}</th><th>{_bi("强度", "Strength")}</th><th>{_bi("置信度", "Confidence")}</th><th>{_bi("Provider", "Provider")}</th></tr></thead><tbody>{signal_rows}</tbody></table>
  </section>
</main>
<script>
  document.querySelectorAll("[data-lang]").forEach((button) => {{
    button.addEventListener("click", () => {{
      document.documentElement.lang = button.dataset.lang;
    }});
  }});
</script>
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
            '<div class="notice danger">'
            f"{_bi('本次运行包含 Mock 数据。未来网页必须在页面入口明确展示该提示。', 'Mock data is present in this run. The future web UI must show this disclosure at the URL level.')}"
            "</div>"
        )
    if status.get("degradation_event_count"):
        return (
            '<div class="notice">'
            f"{_bi('本次使用真实数据源，但记录到 provider fallback 事件：', 'Real providers were used, with provider fallback events recorded: ')}"
            f'{_h(status.get("degradation_event_count"))}. '
            f"{_bi('本次仍然是非 Mock 运行，fallback 已在页面中显式披露。', 'This run remains non-mock, but the fallback is visible for review.')}"
            "</div>"
        )
    return (
        '<div class="notice ok">'
        f"{_bi('所有必需数据层均为真实 provider 数据。', 'All required layers are real provider layers.')}"
        "</div>"
    )


def _holding_row(row: dict[str, Any]) -> str:
    stock = f'{row.get("stock_code")} {row.get("stock_name")}'
    mapping_method = str(row.get("mapping_method") or "")
    return (
        "<tr>"
        f"<td>{_h(stock)}</td>"
        f"<td>{_pct(row.get('weight'))}</td>"
        f"<td>{_narrative_label(row.get('narrative_name'))}</td>"
        f"<td>{_label(mapping_method, MAPPING_METHOD_ZH)} / {_pct(row.get('mapping_confidence'))}</td>"
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
        f"<td>{_label(name, DIMENSION_ZH)}</td>"
        f"<td>{_fmt(value.get('score'))}</td>"
        f"<td>{_h(value.get('supporting_signal_count'))}</td>"
        f"<td>{_h(value.get('risk_signal_count'))}</td>"
        f"<td>{_pct(value.get('confidence'))}</td>"
        "</tr>"
    )


def _radar_chart(primary: dict[str, Any]) -> str:
    dimensions = primary.get("dimensions") or {}
    scores = [
        _dimension_score(dimensions, str(item["key"])) for item in RADAR_DIMENSIONS
    ]
    axis_items = "".join(
        _radar_axis_item(item, score)
        for item, score in zip(RADAR_DIMENSIONS, scores, strict=True)
    )
    return f"""
  <section>
    <h2>{_term("五维雷达图", "Five-Dimension Radar", "把持续性评分拆成五个维度展示。注意：估值风险强度和反向证据强度是风险轴，分数越高代表风险越强。", "Breaks the sustainability score into five dimensions. Note: valuation risk strength and counter-evidence strength are risk axes, where higher means stronger risk.")}</h2>
    <div class="radar-layout">
      <div class="radar-chart" aria-label="{_h('五维雷达图 / Five-dimension radar chart')}">
        {_radar_svg(scores)}
      </div>
      <div>
        <p class="radar-note">{_bi("雷达图展示评分模型的原始维度，不改变持续性评分计算。风险轴已经明确标注为风险强度，不能按“越高越好”解读。", "The radar chart shows raw model dimensions and does not change the sustainability score calculation. Risk axes are explicitly labeled as risk strength and should not be read as higher-is-better.")}</p>
        <div class="axis-list">{axis_items}</div>
      </div>
    </div>
  </section>
"""


def _radar_svg(scores: list[float]) -> str:
    center = 170.0
    radius = 108.0
    max_score = 100.0
    grid_polygons = []
    for fraction in [0.25, 0.5, 0.75, 1.0]:
        points = _radar_points([max_score * fraction] * len(scores), center, radius)
        grid_polygons.append(
            f'<polygon class="radar-grid" points="{_points_attr(points)}" />'
        )
    axes = []
    labels = []
    for index, item in enumerate(RADAR_DIMENSIONS):
        angle = _radar_angle(index, len(RADAR_DIMENSIONS))
        end_x = center + radius * math.cos(angle)
        end_y = center + radius * math.sin(angle)
        label_x = center + (radius + 38) * math.cos(angle)
        label_y = center + (radius + 38) * math.sin(angle)
        anchor = _text_anchor(label_x, center)
        axes.append(
            f'<line class="radar-axis" x1="{center:.1f}" y1="{center:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" />'
        )
        labels.append(
            _svg_label(
                x=label_x,
                y=label_y,
                anchor=anchor,
                zh=str(item["zh"]),
                en=str(item["en"]),
                score=scores[index],
            )
        )
    value_points = _radar_points(scores, center, radius)
    point_marks = "".join(
        f'<circle class="radar-point" cx="{x:.1f}" cy="{y:.1f}" r="3.5" />'
        for x, y in value_points
    )
    return (
        '<svg viewBox="0 0 340 340" role="img">'
        f'<title>{_h("五维雷达图 / Five-Dimension Radar")}</title>'
        f"{''.join(grid_polygons)}"
        f"{''.join(axes)}"
        f'<polygon class="radar-area" points="{_points_attr(value_points)}" />'
        f"{point_marks}"
        f"{''.join(labels)}"
        "</svg>"
    )


def _radar_points(
    scores: list[float],
    center: float,
    radius: float,
) -> list[tuple[float, float]]:
    return [
        (
            center + radius * (score / 100.0) * math.cos(
                _radar_angle(index, len(scores))
            ),
            center + radius * (score / 100.0) * math.sin(
                _radar_angle(index, len(scores))
            ),
        )
        for index, score in enumerate(scores)
    ]


def _radar_angle(index: int, total: int) -> float:
    return -math.pi / 2 + (2 * math.pi * index / total)


def _points_attr(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def _svg_label(
    x: float,
    y: float,
    anchor: str,
    zh: str,
    en: str,
    score: float,
) -> str:
    return (
        f'<text class="radar-label" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">'
        f'<tspan class="lang-zh">{_h(zh)}</tspan>'
        f'<tspan class="lang-en">{_h(en)}</tspan>'
        f'<tspan class="radar-score" x="{x:.1f}" dy="15">{score:.0f}</tspan>'
        "</text>"
    )


def _text_anchor(x: float, center: float) -> str:
    if x > center + 8:
        return "start"
    if x < center - 8:
        return "end"
    return "middle"


def _radar_axis_item(item: dict[str, str], score: float) -> str:
    return (
        '<div class="axis-item">'
        f'{_term(item["zh"], item["en"], item["help_zh"], item["help_en"])}'
        f'<span class="axis-value">{score:.0f}</span>'
        "</div>"
    )


def _dimension_score(dimensions: Any, key: str) -> float:
    if not isinstance(dimensions, dict):
        return 0.0
    value = dimensions.get(key)
    if not isinstance(value, dict):
        return 0.0
    score = value.get("score")
    if not isinstance(score, int | float):
        return 0.0
    return max(0.0, min(100.0, float(score)))


def _source_row(layer: dict[str, Any]) -> str:
    disclosure = "mock" if layer.get("is_mock") else "real"
    source_url = str(layer.get("source_url") or "")
    provider = _h(layer.get("provider_name"))
    if source_url.startswith("http"):
        provider = f'<a href="{_h(source_url)}">{provider}</a>'
    display_name = str(layer.get("display_name") or layer.get("layer") or "")
    data_quality = str(layer.get("data_quality") or "")
    return (
        "<tr>"
        f"<td>{_label(display_name, SOURCE_LAYER_ZH)}</td>"
        f"<td>{provider}</td>"
        f"<td><span class=\"tag\">{_label(data_quality, QUALITY_ZH)}</span></td>"
        f"<td>{_label(disclosure, DISCLOSURE_ZH)}</td>"
        "</tr>"
    )


def _evidence_row(row: dict[str, Any]) -> str:
    source = _h(row.get("source") or "")
    source_url = str(row.get("source_url") or "")
    if source_url.startswith("http"):
        source = f'<a href="{_h(source_url)}">{source}</a>'
    label = (
        _h(row["title"])
        if row.get("title")
        else _label(row.get("type") or row.get("sentiment"), SIGNAL_TYPE_ZH)
    )
    stock = " ".join(
        part
        for part in [
            str(row.get("stock_code") or ""),
            str(row.get("stock_name") or ""),
        ]
        if part
    )
    return (
        "<tr>"
        f"<td>{_h(row.get('event_date'))}</td>"
        f"<td>{_h(stock)}</td>"
        f"<td>{label}</td>"
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
        f"<td>{_label(row.get('signal_type'), SIGNAL_TYPE_ZH)}</td>"
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


def _bi(zh: Any, en: Any) -> str:
    return (
        f'<span class="lang-zh">{_h(zh)}</span>'
        f'<span class="lang-en">{_h(en)}</span>'
    )


def _term(label_zh: Any, label_en: Any, help_zh: Any, help_en: Any) -> str:
    return (
        '<span class="term">'
        f"{_bi(label_zh, label_en)}"
        f"{_help(help_zh, help_en)}"
        "</span>"
    )


def _help(help_zh: Any, help_en: Any) -> str:
    return (
        '<details class="help">'
        f'<summary aria-label="{_h("说明 / Help")}" title="{_h("说明 / Help")}">?</summary>'
        f'<span class="help-card">{_bi(help_zh, help_en)}</span>'
        "</details>"
    )


def _label(value: Any, zh_labels: dict[str, str]) -> str:
    value_text = "" if value is None else str(value)
    return _bi(zh_labels.get(value_text, value_text), value_text)


def _narrative_label(name: Any) -> str:
    name_text = "" if name is None else str(name)
    return _bi(NARRATIVE_ZH.get(name_text, name_text), name_text)


def _stage_label(stage: Any) -> str:
    stage_text = "" if stage is None else str(stage)
    return _bi(STAGE_ZH.get(stage_text, stage_text), stage_text)


def _stage_explanation(primary: dict[str, Any]) -> str:
    stage = str(primary.get("stage") or "")
    en = (primary.get("interpretation") or {}).get("stage_explanation") or ""
    zh_by_stage = {
        "emerging": "该叙事处于萌芽阶段：已有早期证据，但支持信号仍需继续验证。",
        "accelerating": "该叙事处于加速阶段：支持信号正在增强，资金、盈利或动量证据开始形成合力。",
        "mature": "该叙事处于成熟阶段：核心逻辑仍有支撑，但边际变化需要继续观察。",
        "weakening": "该叙事正在走弱：支持信号减弱，或反向证据的重要性上升。",
        "broken": "该叙事已经破裂：反向证据明显压过支持信号，需要重新审视原假设。",
    }
    return _bi(zh_by_stage.get(stage, en), en)


def _fmt(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return _h(value)


def _pct(value: Any, already_percent: bool = False) -> str:
    if not isinstance(value, int | float):
        return _h(value)
    normalized = value if already_percent else value * 100
    return f"{normalized:.1f}%"
