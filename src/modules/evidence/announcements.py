from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from html import unescape
from typing import Any

from src.config import DATA_QUALITY_CONFIDENCE
from src.validation import validate_announcement_evidence_payload

ANNOUNCEMENT_EVIDENCE_VERSION = "announcement-evidence-v1"

_POSITIVE_EARNINGS_KEYWORDS = (
    "业绩预增",
    "预增",
    "扭亏",
    "盈利",
    "利润增长",
    "营业收入增长",
)
_ORDER_KEYWORDS = ("中标", "合同", "订单", "采购协议", "框架协议")
_CAPITAL_SUPPORT_KEYWORDS = ("回购", "增持", "股权激励")
_RISK_KEYWORDS = (
    "业绩预减",
    "预减",
    "预亏",
    "亏损",
    "下滑",
    "减值",
    "风险提示",
    "处罚",
    "立案",
    "问询",
    "监管函",
    "诉讼",
    "仲裁",
    "违约",
    "债务逾期",
    "退市",
    "终止",
)
_FINANCIAL_DISCLOSURE_KEYWORDS = (
    "年度报告",
    "半年度报告",
    "季度报告",
    "一季报",
    "三季报",
)
_GOVERNANCE_KEYWORDS = ("董事会", "监事会", "股东大会")


@dataclass(frozen=True)
class AnnouncementEvidenceProfile:
    evidence_type: str
    sentiment: str
    base_confidence: float
    reason: str


def convert_announcements_to_evidence(
    announcements_payload: dict[str, Any],
    stock_mappings: list[dict[str, Any]],
    as_of_date: str,
) -> dict[str, Any]:
    data_quality = str(announcements_payload.get("data_quality") or "unavailable")
    announcements = announcements_payload.get("announcements")
    if not isinstance(announcements, list):
        announcements = []

    mappings_by_stock = _mappings_by_stock(stock_mappings)
    evidence: list[dict[str, Any]] = []
    unmapped_stock_codes: set[str] = set()
    skipped_count = 0

    for announcement in announcements:
        if not isinstance(announcement, dict):
            skipped_count += 1
            continue

        stock_code = _clean_text(announcement.get("stock_code") or "")
        title = _clean_text(announcement.get("title") or "")
        if not stock_code or not title:
            skipped_count += 1
            continue

        mappings = mappings_by_stock.get(stock_code, [])
        if not mappings:
            unmapped_stock_codes.add(stock_code)
            continue

        profile = classify_announcement(announcement)
        event_date = _event_date(announcement.get("announcement_date"), as_of_date)
        for mapping in mappings:
            evidence.append(
                _to_evidence_item(
                    announcement=announcement,
                    stock_code=stock_code,
                    title=title,
                    mapping=mapping,
                    profile=profile,
                    event_date=event_date,
                    data_quality=data_quality,
                )
            )

    payload = {
        "version": ANNOUNCEMENT_EVIDENCE_VERSION,
        "data_quality": data_quality,
        "evidence": sorted(
            evidence,
            key=lambda item: (
                item["stock_code"],
                item["narrative_id"],
                item["event_date"],
                item["title"],
            ),
        ),
        "missing_stock_codes": sorted(
            str(code) for code in announcements_payload.get("missing_stock_codes", [])
        ),
        "unmapped_stock_codes": sorted(unmapped_stock_codes),
        "skipped_announcement_count": skipped_count,
    }
    validate_announcement_evidence_payload(payload)
    return payload


def classify_announcement(announcement: dict[str, Any]) -> AnnouncementEvidenceProfile:
    title = _clean_text(announcement.get("title") or "")
    category = _clean_text(announcement.get("category") or "")
    searchable_text = f"{title} {category}"

    if _contains_any(searchable_text, _RISK_KEYWORDS):
        return AnnouncementEvidenceProfile(
            evidence_type="risk",
            sentiment="negative",
            base_confidence=0.72,
            reason="risk keyword in announcement title/category",
        )
    if _contains_any(searchable_text, _POSITIVE_EARNINGS_KEYWORDS):
        return AnnouncementEvidenceProfile(
            evidence_type="earnings",
            sentiment="positive",
            base_confidence=0.69,
            reason="earnings-support keyword in announcement title/category",
        )
    if _contains_any(searchable_text, _ORDER_KEYWORDS):
        return AnnouncementEvidenceProfile(
            evidence_type="orders",
            sentiment="positive",
            base_confidence=0.66,
            reason="order or contract keyword in announcement title/category",
        )
    if _contains_any(searchable_text, _CAPITAL_SUPPORT_KEYWORDS):
        return AnnouncementEvidenceProfile(
            evidence_type="capital_flow",
            sentiment="positive",
            base_confidence=0.58,
            reason="capital-support keyword in announcement title/category",
        )
    if _contains_any(searchable_text, _FINANCIAL_DISCLOSURE_KEYWORDS):
        return AnnouncementEvidenceProfile(
            evidence_type="financial_report",
            sentiment="mixed",
            base_confidence=0.52,
            reason="financial disclosure title/category",
        )
    if _contains_any(searchable_text, _GOVERNANCE_KEYWORDS):
        return AnnouncementEvidenceProfile(
            evidence_type="governance",
            sentiment="mixed",
            base_confidence=0.46,
            reason="governance disclosure title/category",
        )
    return AnnouncementEvidenceProfile(
        evidence_type="announcement",
        sentiment="mixed",
        base_confidence=0.4,
        reason="generic announcement metadata",
    )


def _to_evidence_item(
    announcement: dict[str, Any],
    stock_code: str,
    title: str,
    mapping: dict[str, Any],
    profile: AnnouncementEvidenceProfile,
    event_date: str,
    data_quality: str,
) -> dict[str, Any]:
    narrative_id = str(mapping["narrative_id"])
    stock_name = _clean_text(announcement.get("stock_name") or "")
    category = _clean_text(announcement.get("category") or "")
    source_url = announcement.get("source_url")
    mapping_confidence = float(mapping.get("confidence", 0))
    confidence = _confidence(
        base_confidence=profile.base_confidence,
        mapping_confidence=mapping_confidence,
        data_quality=data_quality,
    )
    return {
        "evidence_id": _evidence_id(
            stock_code=stock_code,
            narrative_id=narrative_id,
            title=title,
            event_date=event_date,
            source_url=source_url,
        ),
        "narrative_id": narrative_id,
        "type": profile.evidence_type,
        "source": "cninfo_announcement",
        "source_url": source_url if isinstance(source_url, str) else None,
        "title": title,
        "summary": _summary(
            stock_name=stock_name,
            title=title,
            profile=profile,
            data_quality=data_quality,
        ),
        "sentiment": profile.sentiment,
        "confidence": confidence,
        "event_date": event_date,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "announcement_category": category,
        "provider_data_quality": data_quality,
        "mapping_confidence": mapping_confidence,
        "classification_reason": profile.reason,
    }


def _mappings_by_stock(
    stock_mappings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    mappings_by_stock: dict[str, list[dict[str, Any]]] = {}
    for mapping in stock_mappings:
        stock_code = _clean_text(mapping.get("stock_code") or "")
        narrative_id = mapping.get("narrative_id")
        if not stock_code or not narrative_id:
            continue
        mappings_by_stock.setdefault(stock_code, []).append(mapping)
    return {
        stock_code: sorted(items, key=lambda item: str(item["narrative_id"]))
        for stock_code, items in mappings_by_stock.items()
    }


def _confidence(
    base_confidence: float,
    mapping_confidence: float,
    data_quality: str,
) -> float:
    data_quality_confidence = DATA_QUALITY_CONFIDENCE.get(data_quality, 0.5)
    return round(base_confidence * mapping_confidence * data_quality_confidence, 3)


def _summary(
    stock_name: str,
    title: str,
    profile: AnnouncementEvidenceProfile,
    data_quality: str,
) -> str:
    company = stock_name or "the mapped holding"
    return (
        f"{company} disclosed \"{title}\" through {data_quality}-quality CNINFO "
        f"announcement metadata. V1 classified it as {profile.sentiment} "
        f"{profile.evidence_type} evidence based on {profile.reason}; PDF content "
        "has not been parsed."
    )


def _evidence_id(
    stock_code: str,
    narrative_id: str,
    title: str,
    event_date: str,
    source_url: Any,
) -> str:
    digest = hashlib.sha256(
        f"{stock_code}|{narrative_id}|{event_date}|{title}|{source_url}".encode(
            "utf-8"
        )
    ).hexdigest()[:12]
    return f"EV_ANN_{stock_code}_{narrative_id}_{digest.upper()}"


def _event_date(value: Any, as_of_date: str) -> str:
    candidate = _clean_text(value or "")
    if _is_iso_date(candidate):
        return candidate
    if _is_iso_date(as_of_date):
        return as_of_date
    return "1970-01-01"


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _clean_text(value: Any) -> str:
    text = unescape(str(value)).strip()
    return re.sub(r"<[^>]+>", "", text)
