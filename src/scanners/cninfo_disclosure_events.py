from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.source_event_schema import validate_source_event

CNINFO_DISCLOSURE_EVENTS_VERSION = "cninfo-disclosure-events-v1"
CNINFO_PROVIDER_NAME = "cninfo-announcement"
CNINFO_PROVIDER_VERSION = "cninfo-announcement-v1"

CLASSIFICATION_RULES = (
    (
        "major_contract_order",
        "重大合同/订单",
        "positive",
        ("重大合同", "合同", "订单", "中标", "项目中选", "采购协议"),
    ),
    (
        "investment_project",
        "投资项目",
        "positive",
        ("对外投资", "投资项目", "项目投资", "设立子公司", "合资公司"),
    ),
    (
        "capacity_expansion",
        "产能扩张",
        "positive",
        ("扩产", "产能", "生产基地", "项目建设", "投产", "开工建设"),
    ),
    (
        "ma_restructuring",
        "并购重组",
        "mixed",
        ("并购", "收购", "重组", "资产重组", "发行股份购买资产", "重大资产"),
    ),
    (
        "regulatory_inquiry_penalty",
        "监管问询/处罚",
        "negative",
        ("问询函", "监管函", "处罚", "行政处罚", "立案", "调查", "纪律处分"),
    ),
    (
        "performance_forecast_report",
        "业绩预告/报告",
        "mixed",
        ("业绩预告", "业绩快报", "年度报告", "季度报告", "一季度报告", "半年度报告", "三季度报告"),
    ),
    (
        "shareholder_meeting_governance",
        "股东大会/治理",
        "neutral",
        ("股东大会", "股东会", "董事会", "监事会", "法律意见书", "治理", "独立董事"),
    ),
    (
        "financing_refinancing",
        "融资/再融资",
        "mixed",
        ("再融资", "定增", "向特定对象发行", "可转债", "配股", "募集资金", "融资"),
    ),
    (
        "litigation_arbitration",
        "诉讼/仲裁",
        "negative",
        ("诉讼", "仲裁", "起诉", "判决", "裁决"),
    ),
    (
        "risk_warning",
        "风险警示",
        "negative",
        ("风险提示", "风险警示", "退市风险", "*ST", "ST ", "终止上市"),
    ),
)


def classify_cninfo_disclosure_event(announcement: dict[str, Any]) -> dict[str, str]:
    searchable = f"{_clean_text(announcement.get('title'))} {_clean_text(announcement.get('category'))}".upper()
    for event_class, label_zh, sentiment, keywords in CLASSIFICATION_RULES:
        if any(keyword.upper() in searchable for keyword in keywords):
            return {
                "event_class": event_class,
                "event_label_zh": label_zh,
                "sentiment": sentiment,
                "unsupported_category_reason": "",
            }
    return {
        "event_class": "unknown_metadata",
        "event_label_zh": "未支持分类公告",
        "sentiment": "neutral",
        "unsupported_category_reason": "no_supported_keyword_match",
    }


def build_cninfo_disclosure_event_report(
    *,
    announcements_payload: dict[str, Any],
    fetched_at: str | None = None,
) -> dict[str, Any]:
    retrieved_at = fetched_at or _utc_now()
    announcements = [
        item
        for item in announcements_payload.get("announcements", [])
        if isinstance(item, dict)
    ]
    events = [
        _source_event_from_announcement(announcement, fetched_at=retrieved_at)
        for announcement in announcements
        if _clean_text(announcement.get("title"))
    ]
    unknown_count = sum(
        1
        for event in events
        if event["source_metadata"]["event_class"] == "unknown_metadata"
    )
    missing_stock_codes = [
        str(item) for item in announcements_payload.get("missing_stock_codes", [])
    ]
    return {
        "version": CNINFO_DISCLOSURE_EVENTS_VERSION,
        "provider_name": CNINFO_PROVIDER_NAME,
        "provider_version": CNINFO_PROVIDER_VERSION,
        "fetched_at": retrieved_at,
        "data_quality": str(announcements_payload.get("data_quality") or "unavailable"),
        "source_trust_tier": "trusted_fact",
        "evidence_granularity": "metadata_only",
        "summary": {
            "announcement_count": len(announcements),
            "event_count": len(events),
            "unknown_category_count": unknown_count,
            "missing_stock_code_count": len(missing_stock_codes),
            "source_quality": str(announcements_payload.get("data_quality") or "unavailable"),
        },
        "events": events,
        "missing_stock_codes": sorted(missing_stock_codes),
        "degradation_events": _degradation_events(announcements_payload),
    }


def render_cninfo_disclosure_event_html(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>CNINFO 官方公告事件分类</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>CNINFO 官方公告事件分类</h1>",
            '<section class="summary">',
            "<p>来源为 CNINFO 官方公告 metadata；本切片不解析 PDF 正文、不使用 LLM、不触发自动叙事 promotion。</p>",
            _html_kv("公告数", summary.get("announcement_count", 0)),
            _html_kv("事件数", summary.get("event_count", 0)),
            _html_kv("未知分类", summary.get("unknown_category_count", 0)),
            _html_kv("数据质量", summary.get("source_quality", "")),
            _html_kv("信任层级", report.get("source_trust_tier", "")),
            _html_kv("证据粒度", report.get("evidence_granularity", "")),
            "</section>",
            _events_table(_list(report.get("events"))),
            _degradation_table(_list(report.get("degradation_events"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _source_event_from_announcement(
    announcement: dict[str, Any],
    *,
    fetched_at: str,
) -> dict[str, Any]:
    classification = classify_cninfo_disclosure_event(announcement)
    stock_code = _clean_text(announcement.get("stock_code"))
    stock_name = _clean_text(announcement.get("stock_name"))
    title = _clean_text(announcement.get("title"))
    category = _clean_text(announcement.get("category"))
    event_time = _clean_text(announcement.get("announcement_date"))
    source_url = _clean_text(announcement.get("source_url"))
    source_metadata = {
        "provider": CNINFO_PROVIDER_NAME,
        "provider_version": CNINFO_PROVIDER_VERSION,
        "permission_status": "public_official_disclosure",
        "degradation_state": "ok",
        "source_mode": "external_contract",
        "stock_code": stock_code,
        "stock_name": stock_name,
        "announcement_category": category,
        "event_class": classification["event_class"],
        "event_label_zh": classification["event_label_zh"],
        "sentiment": classification["sentiment"],
        "fetched_at": fetched_at,
        "source_trust_tier": "trusted_fact",
        "evidence_granularity": "metadata_only",
        "pdf_body_parsed": False,
        "raw_hash": _raw_hash(announcement),
    }
    if classification["unsupported_category_reason"]:
        source_metadata["unsupported_category_reason"] = classification[
            "unsupported_category_reason"
        ]
    event = validate_source_event(
        {
            "event_id": _stable_id(
                "EVT_CNINFO",
                [stock_code, event_time, title, source_url],
            ),
            "source_type": "announcement",
            "provider": CNINFO_PROVIDER_NAME,
            "provider_version": CNINFO_PROVIDER_VERSION,
            "source_url": source_url,
            "event_time": event_time,
            "title": title,
            "summary": (
                f"{stock_name or stock_code} CNINFO announcement metadata classified as "
                f"{classification['event_class']}; PDF body was not parsed."
            ),
            "stock_codes": [stock_code] if stock_code else [],
            "mentioned_stocks": [
                {"stock_code": stock_code, "stock_name": stock_name}
            ]
            if stock_code
            else [],
            "narrative_hints": [classification["event_label_zh"], category],
            "evidence_claims": [
                f"CNINFO metadata reports {title} with category {category}."
            ],
            "source_metadata": source_metadata,
        }
    )
    return {
        **event,
        "source_trust_tier": "trusted_fact",
        "evidence_granularity": "metadata_only",
    }


def _degradation_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    missing = [str(item) for item in payload.get("missing_stock_codes", [])]
    if not missing:
        return []
    return [
        {
            "type": "missing_stock_codes",
            "provider_name": CNINFO_PROVIDER_NAME,
            "reason": f"CNINFO returned no usable announcement rows for: {', '.join(sorted(missing))}",
        }
    ]


def _events_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>公告事件</h2><p>没有可展示事件。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("日期", "股票", "标题", "分类", "事件类型", "Trust", "URL")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('event_time'))}</td>"
        f"<td>{_html_text(','.join(_list(row.get('stock_codes'))))}</td>"
        f"<td>{_html_text(row.get('title'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('announcement_category'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('event_class'))}</td>"
        f"<td>{_html_text(row.get('source_trust_tier'))}</td>"
        f"<td>{_html_text(row.get('source_url'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>公告事件</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _degradation_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>降级事件</h2><p>没有降级事件。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for label in ("类型", "Provider", "原因"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('type'))}</td>"
        f"<td>{_html_text(row.get('provider_name'))}</td>"
        f"<td>{_html_text(row.get('reason'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>降级事件</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _raw_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1(
        "|".join(str(value or "") for value in values).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16].upper()}"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
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


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
