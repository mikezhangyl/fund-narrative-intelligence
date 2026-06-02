from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

VALUE_DISPLAY = {
    "unknown": "未知",
    "completed": "已完成",
    "ok": "正常",
    "passed": "通过",
    "pass": "通过",
    "partial": "部分完成",
    "degraded": "已降级",
    "Blocked": "已阻塞",
    "blocked": "已阻塞",
    "missing": "缺失",
    "fresh": "新鲜",
    "breached": "已超期",
    "generated": "已生成",
    "artifact_reported": "产物报告",
    "service_reported": "服务报告",
    "generated_artifact": "生成产物",
    "live_api": "实时 API",
    "fixture_demo": "示例产物",
    "narrative_service": "叙事服务",
    "Narrative quality audit": "叙事质量审计",
    "Portfolio narrative workspace": "组合叙事工作台",
    "Production readiness assistant": "生产就绪助手",
    "Product shell": "产品壳",
    "Product shell route registry": "产品壳路由注册表",
    "Artifact index": "产物索引",
    "Source Investigation Gate Pack": "来源调查准入包",
    "Tushare News Permission Smoke": "Tushare 新闻权限实时检查",
    "Narrative Source Decision Matrix": "叙事来源决策矩阵",
    "Source Quality Dashboard": "来源质量仪表盘",
    "Narrative Data": "真实叙事数据",
    "Config Preflight": "配置与预检",
    "Workspace State": "本地工作区状态",
    "Workspace Export": "工作区导出包",
    "Real Fund Smoke Summary": "真实基金冒烟摘要",
    "Announcement Evidence Smoke Summary": "公告证据冒烟摘要",
    "Candidate Review Action Act Reject Persist Test Persistence": "候选复核拒绝操作持久化测试",
    "Narrative Governance Audit Export": "叙事治理审计导出",
    "Narrative Service Provider Smoke": "叙事服务供应商冒烟",
    "Narrative Service Conformance Report": "叙事服务契约符合性报告",
    "Fund Holding Exposure Report": "基金持仓暴露报告",
    "Acceptance Summary": "验收摘要",
    "Review Actions": "复核操作",
    "Live Validation Dashboard": "实时验证仪表盘",
    "Narrative Source Gateway Probe": "叙事来源网关探测",
    "Source Governance Report": "来源治理报告",
    "Source Schema V2 Report": "来源结构 v2 报告",
    "Source Reliability Report": "来源可靠性报告",
    "Source Feasibility Matrix": "来源可行性矩阵",
    "Cninfo Disclosure Events": "巨潮公告事件",
    "Public News Context": "公共新闻上下文",
    "Sec Edgar Source Smoke": "SEC EDGAR 来源冒烟",
    "Stocktwits Heat Signal": "Stocktwits 热度信号",
    "Fresh Narrative Digest": "最新叙事摘要",
    "Narrative Timeline Search": "叙事时间线搜索",
    "Narrative Evidence Graph": "叙事证据图谱",
    "Release Manifest": "发布清单",
    "Acceptance Checklist": "验收检查表",
    "Narrative Research Export Pack": "叙事研究导出包",
    "Historical Replay Run": "历史回放运行",
    "Replay Stability Evaluation": "回放稳定性评估",
    "Replay Alert Review": "回放告警复核",
    "Collaboration Handoff Bundle": "协作交接包",
    "Backup Restore Archive Manifest": "备份恢复归档清单",
    "Operator Release Readiness": "操作员发布就绪",
    "persisted": "已持久化",
}


def build_product_shell_payload(
    *,
    route_registry: dict[str, Any],
    artifact_index: dict[str, Any],
    narrative_data: dict[str, Any] | None = None,
    workspace_state: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    routes = _list(route_registry.get("routes"))
    artifacts = _list(artifact_index.get("artifacts"))
    narrative_summary = _mapping(_mapping(narrative_data).get("summary"))
    workspace_summary = _mapping(_mapping(workspace_state).get("summary"))
    return {
        "version": "product-shell-v1",
        "generated_at": generated_at or _utc_now(),
        "summary": {
            "route_count": len(routes),
            "artifact_count": len(artifacts),
            "narrative_count": _int(narrative_summary.get("narrative_count")),
            "candidate_narrative_count": _int(narrative_summary.get("candidate_narrative_count")),
            "stock_mapping_count": _int(narrative_summary.get("stock_mapping_count")),
            "evidence_pack_count": _int(narrative_summary.get("evidence_pack_count")),
            "quality_issue_count": _int(narrative_summary.get("quality_issue_count")),
            "extraction_issue_count": _int(narrative_summary.get("extraction_issue_count")),
            "live_api_route_count": _int(_mapping(route_registry.get("summary")).get("live_api_route_count")),
            "generated_artifact_route_count": _int(
                _mapping(route_registry.get("summary")).get("generated_artifact_route_count")
            ),
            "workspace_saved_view_count": _int(workspace_summary.get("saved_view_count")),
        },
        "route_registry": route_registry,
        "artifact_index": artifact_index,
        "narrative_data": narrative_data or {},
        "workspace_state": workspace_state or {},
        "client_policy_notice": "不在页面内重算雷达、质量或组合指标；页面只读取服务 API 或生成产物。",
    }


def render_product_home_html(shell: dict[str, Any]) -> str:
    summary = _mapping(shell.get("summary"))
    routes = _list(_mapping(shell.get("route_registry")).get("routes"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>Fund Narrative Intelligence 产品首页</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>Fund Narrative Intelligence 产品首页</h1>",
            '<section class="summary">',
            _html_kv("路由数", summary.get("route_count", 0)),
            _html_kv("产物数", summary.get("artifact_count", 0)),
            f"<p>{_html_text(shell.get('client_policy_notice'))}</p>",
            "</section>",
            _narrative_data_summary(shell),
            _workspace_state_summary(shell),
            _route_cards(routes),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def render_artifact_browser_html(shell: dict[str, Any]) -> str:
    artifacts = _list(_mapping(shell.get("artifact_index")).get("artifacts"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>产物浏览器</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>产物浏览器</h1>",
            "<p>这里集中列出本地已生成的 JSON/HTML 产物、运行目录、状态、告警和新鲜度。</p>",
            _artifact_table(artifacts),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _workspace_state_summary(shell: dict[str, Any]) -> str:
    summary = _mapping(shell.get("summary"))
    return (
        "<section>"
        "<h2>本地工作区</h2>"
        '<div class="facts">'
        f"<p>保存视图: {_html_text(summary.get('workspace_saved_view_count', 0))}</p>"
        "</div>"
        "<p>查看 workspace_state.html 获取本地保存视图、过滤器、排序和迁移契约。</p>"
        "</section>"
    )


def _narrative_data_summary(shell: dict[str, Any]) -> str:
    summary = _mapping(shell.get("summary"))
    source_count = len(_list(_mapping(shell.get("narrative_data")).get("source_artifacts")))
    return (
        "<section>"
        "<h2>真实叙事数据</h2>"
        '<div class="facts">'
        f"<p>正式叙事: {_html_text(summary.get('narrative_count', 0))}</p>"
        f"<p>候选叙事: {_html_text(summary.get('candidate_narrative_count', 0))}</p>"
        f"<p>股票映射: {_html_text(summary.get('stock_mapping_count', 0))}</p>"
        f"<p>证据包: {_html_text(summary.get('evidence_pack_count', 0))}</p>"
        f"<p>质量问题: {_html_text(summary.get('quality_issue_count', 0))}</p>"
        f"<p>抽取复核项: {_html_text(summary.get('extraction_issue_count', 0))}</p>"
        f"<p>来源 artifact: {_html_text(source_count)}</p>"
        "</div>"
        "<p>查看 narrative_data.html 获取现有 Narrative Service / registry artifact 明细。</p>"
        "</section>"
    )


def _route_cards(routes: list[Any]) -> str:
    cards = []
    for route in routes:
        row = _mapping(route)
        data_source = _mapping(row.get("data_source"))
        cards.append(
            '<article class="card">'
            f"<h2>{_html_text(row.get('label_zh'))}</h2>"
            f"<p><strong>路由:</strong> {_html_text(row.get('path'))}</p>"
            f"<p><strong>负责人:</strong> {_html_text(row.get('owner_service'))}</p>"
            f"<p><strong>数据:</strong> {_html_text(_display_value(data_source.get('type')))} / {_html_text(_display_value(data_source.get('freshness_status')))}</p>"
            f"<p><strong>来源:</strong> {_html_text(data_source.get('source'))}</p>"
            "</article>"
        )
    return f"<section><h2>导航</h2><div class=\"cards\">{''.join(cards)}</div></section>"


def _artifact_table(artifacts: list[Any]) -> str:
    rows = [_mapping(artifact) for artifact in artifacts]
    if not rows:
        return "<section><h2>产物列表</h2><p>没有找到可展示产物。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("产物", "运行", "状态", "新鲜度", "HTML", "JSON")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(_display_value(row.get('surface')))}</td>"
        f"<td>{_html_text(row.get('run_id'))}</td>"
        f"<td>{_html_text(_display_value(row.get('status')))}</td>"
        f"<td>{_html_text(_display_value(row.get('freshness_status')))}</td>"
        f"<td>{_html_text(row.get('html_path'))}</td>"
        f"<td>{_html_text(row.get('json_path'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>产物列表</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value or "")
    fund_surface = _fund_surface_display(text)
    if fund_surface:
        return fund_surface
    return VALUE_DISPLAY.get(text, text)


def _fund_surface_display(text: str) -> str:
    parts = text.split()
    if len(parts) >= 3 and parts[0] == "Fund" and parts[1].isdigit():
        suffix = " ".join(parts[2:])
        suffix_display = {
            "Raw": "原始数据",
            "Scoring": "评分",
            "Review Queue": "复核队列",
            "Manifest": "清单",
            "Source Table": "来源表",
            "Workspace Snapshot": "工作区快照",
            "Signal Trace": "信号追踪",
            "Demo": "演示页",
        }.get(suffix)
        if suffix_display:
            return f"基金 {parts[1]} {suffix_display}"
    return ""


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
.facts p { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; margin: 0; padding: 12px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.card { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 14px; }
.card h2 { margin-top: 0; font-size: 18px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
