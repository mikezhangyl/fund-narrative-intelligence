from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

SOURCE_CATALOG_VERSION = "narrative-source-catalog-v1"
COMPANY_FACT_VERSION = "narrative-company-facts-v1"

_GENERIC_TERMS = {
    "announcement",
    "announcements",
    "article",
    "articles",
    "capital",
    "company",
    "companies",
    "co",
    "corp",
    "corporation",
    "data",
    "change",
    "evidence",
    "finance",
    "financial",
    "growth",
    "group",
    "headline",
    "holdings",
    "inc",
    "industry",
    "latest",
    "limited",
    "ltd",
    "market",
    "metrics",
    "narrative",
    "net",
    "parent",
    "performance",
    "price",
    "profit",
    "provider",
    "report",
    "reports",
    "revenue",
    "shares",
    "signal",
    "signals",
    "snapshot",
    "stock",
    "stocks",
    "theme",
    "valuation",
    "yoy",
    "for",
    "公告",
    "公司",
    "增长",
    "基金",
    "市场",
    "数据",
    "指标",
    "行业",
    "股票",
    "证券",
    "财务",
    "新闻",
    "叙事",
}


def build_source_catalog(
    *,
    holdings: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    announcements_payload: dict[str, Any] | None = None,
    market_quotes_payload: dict[str, Any] | None = None,
    valuation_snapshots_payload: dict[str, Any] | None = None,
    financial_metrics_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    holdings_by_stock = {
        str(holding.get("stock_code") or ""): holding for holding in holdings
    }
    items = [
        *_evidence_source_items(evidence=evidence, holdings_by_stock=holdings_by_stock),
        *_announcement_source_items(
            announcements_payload=announcements_payload,
            holdings_by_stock=holdings_by_stock,
        ),
        *_market_quote_source_items(
            market_quotes_payload=market_quotes_payload,
            holdings_by_stock=holdings_by_stock,
        ),
        *_valuation_source_items(
            valuation_snapshots_payload=valuation_snapshots_payload,
            holdings_by_stock=holdings_by_stock,
        ),
        *_financial_metric_source_items(
            financial_metrics_payload=financial_metrics_payload,
            holdings_by_stock=holdings_by_stock,
        ),
    ]
    company_facts = _build_company_facts(items)
    return {
        "version": SOURCE_CATALOG_VERSION,
        "items": items,
        "stats": _source_catalog_stats(items),
        "company_facts": company_facts,
        "company_fact_stats": _company_fact_stats(company_facts),
    }


def _evidence_source_items(
    *,
    evidence: list[dict[str, Any]],
    holdings_by_stock: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    items = []
    for item in evidence:
        evidence_id = str(item.get("evidence_id") or "")
        if not evidence_id:
            continue
        stock_code = str(item.get("stock_code") or "")
        holding = holdings_by_stock.get(stock_code, {})
        title = str(item.get("title") or "")
        summary = str(item.get("summary") or "")
        items.append(
            {
                "source_item_id": f"SRC_EVIDENCE_{evidence_id}",
                "source_type": "evidence",
                "provider_name": str(item.get("source") or "evidence"),
                "provider_version": None,
                "source_url": item.get("source_url"),
                "stock_code": stock_code or None,
                "stock_name": item.get("stock_name") or holding.get("stock_name"),
                "industry": holding.get("industry"),
                "holding_weight": holding.get("weight"),
                "narrative_id": item.get("narrative_id"),
                "event_date": item.get("event_date"),
                "title": title,
                "summary": summary,
                "sentiment": item.get("sentiment"),
                "confidence": item.get("confidence"),
                "evidence_type": item.get("type"),
                "terms": extract_terms(
                    [
                        title,
                        summary,
                        str(item.get("type") or ""),
                        str(holding.get("stock_name") or ""),
                        str(holding.get("industry") or ""),
                    ]
                ),
                "source_ref_id": evidence_id,
            }
        )
    return items


def _announcement_source_items(
    *,
    announcements_payload: dict[str, Any] | None,
    holdings_by_stock: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not announcements_payload:
        return []
    items = []
    provider_name = str(announcements_payload.get("provider_name") or "announcements")
    provider_version = announcements_payload.get("provider_version")
    for announcement in announcements_payload.get("announcements") or []:
        stock_code = str(announcement.get("stock_code") or "")
        title = str(announcement.get("title") or "")
        if not stock_code or not title:
            continue
        holding = holdings_by_stock.get(stock_code, {})
        source_url = announcement.get("source_url")
        source_ref = source_url or title
        items.append(
            {
                "source_item_id": _source_item_id(
                    prefix="SRC_ANNOUNCEMENT",
                    components=[stock_code, title, str(source_ref)],
                ),
                "source_type": "announcement",
                "provider_name": provider_name,
                "provider_version": provider_version,
                "source_url": source_url,
                "stock_code": stock_code,
                "stock_name": announcement.get("stock_name") or holding.get("stock_name"),
                "industry": holding.get("industry"),
                "holding_weight": holding.get("weight"),
                "narrative_id": None,
                "event_date": announcement.get("announcement_date"),
                "title": title,
                "summary": str(announcement.get("category") or ""),
                "sentiment": None,
                "confidence": None,
                "announcement_category": announcement.get("category"),
                "terms": extract_terms(
                    [
                        title,
                        str(announcement.get("category") or ""),
                        str(announcement.get("stock_name") or ""),
                        str(holding.get("industry") or ""),
                    ]
                ),
                "source_ref_id": source_ref,
            }
        )
    return items


def _market_quote_source_items(
    *,
    market_quotes_payload: dict[str, Any] | None,
    holdings_by_stock: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not market_quotes_payload:
        return []
    provider_name = str(market_quotes_payload.get("provider_name") or "market_quotes")
    provider_version = market_quotes_payload.get("provider_version")
    items = []
    for quote in market_quotes_payload.get("quotes") or []:
        stock_code = str(quote.get("stock_code") or "")
        if not stock_code:
            continue
        holding = holdings_by_stock.get(stock_code, {})
        change_percent = quote.get("change_percent")
        title = f"Quote snapshot for {quote.get('stock_name') or stock_code}"
        summary = (
            f"Latest price {quote.get('latest_price')}, change {change_percent}%."
            if change_percent is not None
            else "Latest price snapshot."
        )
        items.append(
            {
                "source_item_id": _source_item_id(
                    prefix="SRC_QUOTE",
                    components=[stock_code, str(quote.get("retrieved_at") or "")],
                ),
                "source_type": "market_quote",
                "provider_name": provider_name,
                "provider_version": provider_version,
                "source_url": market_quotes_payload.get("source_url"),
                "stock_code": stock_code,
                "stock_name": quote.get("stock_name") or holding.get("stock_name"),
                "industry": holding.get("industry"),
                "holding_weight": holding.get("weight"),
                "narrative_id": None,
                "event_date": quote.get("retrieved_at"),
                "title": title,
                "summary": summary,
                "sentiment": _quote_sentiment(change_percent),
                "confidence": 0.55,
                "change_percent": change_percent,
                "latest_price": quote.get("latest_price"),
                "terms": extract_terms(
                    [
                        str(holding.get("stock_name") or quote.get("stock_name") or ""),
                        str(holding.get("industry") or ""),
                        summary,
                    ]
                ),
                "source_ref_id": stock_code,
            }
        )
    return items


def _valuation_source_items(
    *,
    valuation_snapshots_payload: dict[str, Any] | None,
    holdings_by_stock: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not valuation_snapshots_payload:
        return []
    provider_name = str(
        valuation_snapshots_payload.get("provider_name") or "valuation_snapshots"
    )
    provider_version = valuation_snapshots_payload.get("provider_version")
    items = []
    for valuation in valuation_snapshots_payload.get("valuations") or []:
        stock_code = str(valuation.get("stock_code") or "")
        if not stock_code:
            continue
        holding = holdings_by_stock.get(stock_code, {})
        pressure = str(valuation.get("valuation_pressure") or "unknown")
        title = f"Valuation snapshot for {valuation.get('stock_name') or stock_code}"
        summary = (
            f"Valuation pressure {pressure}; PE {valuation.get('pe_ttm')} and PB {valuation.get('pb')}."
        )
        items.append(
            {
                "source_item_id": _source_item_id(
                    prefix="SRC_VALUATION",
                    components=[stock_code, str(valuation.get("retrieved_at") or "")],
                ),
                "source_type": "valuation_snapshot",
                "provider_name": provider_name,
                "provider_version": provider_version,
                "source_url": valuation.get("source_url")
                or valuation_snapshots_payload.get("source_url"),
                "stock_code": stock_code,
                "stock_name": valuation.get("stock_name") or holding.get("stock_name"),
                "industry": holding.get("industry"),
                "holding_weight": holding.get("weight"),
                "narrative_id": None,
                "event_date": valuation.get("retrieved_at"),
                "title": title,
                "summary": summary,
                "sentiment": _valuation_sentiment(pressure),
                "confidence": 0.58,
                "valuation_pressure": pressure,
                "pe_ttm": valuation.get("pe_ttm"),
                "pb": valuation.get("pb"),
                "terms": extract_terms(
                    [
                        str(
                            holding.get("stock_name")
                            or valuation.get("stock_name")
                            or ""
                        ),
                        str(holding.get("industry") or ""),
                        pressure,
                        summary,
                    ]
                ),
                "source_ref_id": stock_code,
            }
        )
    return items


def _financial_metric_source_items(
    *,
    financial_metrics_payload: dict[str, Any] | None,
    holdings_by_stock: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not financial_metrics_payload:
        return []
    provider_name = str(
        financial_metrics_payload.get("provider_name") or "financial_metrics"
    )
    provider_version = financial_metrics_payload.get("provider_version")
    items = []
    for metric in financial_metrics_payload.get("metrics") or []:
        stock_code = str(metric.get("stock_code") or "")
        if not stock_code:
            continue
        holding = holdings_by_stock.get(stock_code, {})
        title = f"Financial metrics for {metric.get('stock_name') or stock_code}"
        summary = (
            f"Report {metric.get('report_type')} as of {metric.get('report_date')}; "
            f"revenue YoY {metric.get('revenue_yoy')}, parent net profit YoY {metric.get('parent_net_profit_yoy')}."
        )
        items.append(
            {
                "source_item_id": _source_item_id(
                    prefix="SRC_FINANCIAL",
                    components=[stock_code, str(metric.get("report_date") or "")],
                ),
                "source_type": "financial_metric",
                "provider_name": provider_name,
                "provider_version": provider_version,
                "source_url": metric.get("source_url")
                or financial_metrics_payload.get("source_url"),
                "stock_code": stock_code,
                "stock_name": metric.get("stock_name") or holding.get("stock_name"),
                "industry": holding.get("industry"),
                "holding_weight": holding.get("weight"),
                "narrative_id": None,
                "event_date": metric.get("report_date"),
                "title": title,
                "summary": summary,
                "sentiment": _financial_sentiment(metric),
                "confidence": 0.62,
                "report_type": metric.get("report_type"),
                "report_date": metric.get("report_date"),
                "revenue_yoy": metric.get("revenue_yoy"),
                "parent_net_profit_yoy": metric.get("parent_net_profit_yoy"),
                "terms": extract_terms(
                    [
                        str(
                            holding.get("stock_name")
                            or metric.get("stock_name")
                            or ""
                        ),
                        str(holding.get("industry") or ""),
                        str(metric.get("report_type") or ""),
                        summary,
                    ]
                ),
                "source_ref_id": stock_code,
            }
        )
    return items


def _source_catalog_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_type = Counter(str(item.get("source_type") or "") for item in items)
    by_provider = Counter(str(item.get("provider_name") or "") for item in items)
    by_stock = Counter(
        str(item.get("stock_code") or "")
        for item in items
        if item.get("stock_code")
    )
    return {
        "item_count": len(items),
        "source_type_counts": dict(sorted(by_type.items())),
        "provider_counts": dict(sorted(by_provider.items())),
        "stock_coverage_count": len(by_stock),
    }


def _build_company_facts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _company_fact_from_source_item(item)
        for item in items
        if item.get("source_item_id") and item.get("stock_code")
    ]


def _company_fact_from_source_item(item: dict[str, Any]) -> dict[str, Any]:
    fact_type, fact_direction = _classify_fact(item)
    source_type = str(item.get("source_type") or "")
    stock_name = str(item.get("stock_name") or "")
    source_item_id = str(item.get("source_item_id") or "")
    numeric_only = source_type in {"market_quote", "valuation_snapshot"}
    narrative_ready = source_type in {"announcement", "evidence", "financial_metric"}
    return {
        "version": COMPANY_FACT_VERSION,
        "company_fact_id": _source_item_id(
            prefix="FACT",
            components=[source_item_id, fact_type, fact_direction],
        ),
        "stock_code": item.get("stock_code"),
        "stock_name": item.get("stock_name"),
        "industry": item.get("industry"),
        "holding_weight": item.get("holding_weight"),
        "event_date": item.get("event_date"),
        "source_type": source_type,
        "provider_name": item.get("provider_name"),
        "source_url": item.get("source_url"),
        "fact_type": fact_type,
        "fact_direction": fact_direction,
        "fact_confidence": item.get("confidence"),
        "fact_summary_zh": _fact_summary_zh(
            stock_name=stock_name,
            fact_type=fact_type,
            fact_direction=fact_direction,
            item=item,
        ),
        "fact_summary_en": _fact_summary_en(item, fact_type),
        "company_keywords_zh": _language_keywords(
            [stock_name, str(item.get("industry") or "")],
            want_cjk=True,
        ),
        "company_keywords_en": _language_keywords(
            [stock_name, str(item.get("industry") or "")],
            want_cjk=False,
        ),
        "event_keywords_zh": _language_keywords(item.get("terms") or [], want_cjk=True),
        "event_keywords_en": _language_keywords(
            item.get("terms") or [],
            want_cjk=False,
        ),
        "supporting_source_item_ids": [source_item_id],
        "narrative_ready": narrative_ready,
        "is_numeric_only": numeric_only,
    }


def _company_fact_stats(company_facts: list[dict[str, Any]]) -> dict[str, Any]:
    fact_types = Counter(str(item.get("fact_type") or "") for item in company_facts)
    directions = Counter(
        str(item.get("fact_direction") or "") for item in company_facts
    )
    stock_codes = {
        str(item.get("stock_code") or "") for item in company_facts if item.get("stock_code")
    }
    return {
        "fact_count": len(company_facts),
        "fact_type_counts": dict(sorted(fact_types.items())),
        "fact_direction_counts": dict(sorted(directions.items())),
        "stock_coverage_count": len(stock_codes),
        "narrative_ready_fact_count": sum(
            1 for item in company_facts if item.get("narrative_ready")
        ),
        "numeric_only_fact_count": sum(
            1 for item in company_facts if item.get("is_numeric_only")
        ),
    }


def _classify_fact(item: dict[str, Any]) -> tuple[str, str]:
    source_type = str(item.get("source_type") or "")
    if source_type == "announcement":
        category = str(item.get("announcement_category") or "").lower()
        category_map = {
            "order": ("订单进展", "positive"),
            "expansion": ("产能扩张", "positive"),
            "guidance": ("经营指引", "positive"),
            "results": ("业绩披露", "mixed"),
            "earnings": ("业绩披露", "mixed"),
            "risk": ("风险提示", "negative"),
        }
        if category in category_map:
            return category_map[category]
        return ("公告进展", "mixed")
    if source_type == "market_quote":
        sentiment = str(item.get("sentiment") or "")
        if sentiment == "positive":
            return ("股价上涨", "positive")
        if sentiment == "negative":
            return ("股价回撤", "negative")
        return ("股价波动", "mixed")
    if source_type == "valuation_snapshot":
        pressure = str(item.get("valuation_pressure") or "")
        if pressure == "discounted":
            return ("估值折价", "positive")
        if pressure == "elevated":
            return ("估值承压", "negative")
        return ("估值波动", "mixed")
    if source_type == "financial_metric":
        revenue_yoy = item.get("revenue_yoy")
        profit_yoy = item.get("parent_net_profit_yoy")
        if isinstance(revenue_yoy, int | float) and isinstance(profit_yoy, int | float):
            if revenue_yoy > 0 and profit_yoy > 0:
                return ("业绩增长", "positive")
            if revenue_yoy < 0 and profit_yoy < 0:
                return ("业绩下滑", "negative")
        return ("业绩分化", "mixed")
    sentiment = str(item.get("sentiment") or "")
    if sentiment == "positive":
        return ("业务进展", "positive")
    if sentiment == "negative":
        return ("经营承压", "negative")
    return ("业务动态", "mixed")


def _fact_summary_zh(
    *,
    stock_name: str,
    fact_type: str,
    fact_direction: str,
    item: dict[str, Any],
) -> str:
    company = stock_name or str(item.get("stock_code") or "相关公司")
    source_type = str(item.get("source_type") or "")
    if source_type == "announcement":
        title = str(item.get("title") or "")
        return f"{company}{fact_type}：{title or '公告披露相关进展'}。"
    if source_type == "financial_metric":
        report_type = str(item.get("report_type") or "最新财报")
        revenue_yoy = item.get("revenue_yoy")
        profit_yoy = item.get("parent_net_profit_yoy")
        return (
            f"{company}{report_type}{fact_type}，营收同比{revenue_yoy}，"
            f"归母净利润同比{profit_yoy}。"
        )
    if source_type == "market_quote":
        change_percent = item.get("change_percent")
        return f"{company}{fact_type}，最新涨跌幅{change_percent}%。"
    if source_type == "valuation_snapshot":
        return f"{company}{fact_type}，当前估值状态为{item.get('valuation_pressure')}。"
    direction_text = {
        "positive": "出现利好线索",
        "negative": "出现承压线索",
        "mixed": "出现中性动态",
    }.get(fact_direction, "出现相关动态")
    return f"{company}{fact_type}，{direction_text}。"


def _fact_summary_en(item: dict[str, Any], fact_type: str) -> str:
    title = str(item.get("title") or "").strip()
    summary = str(item.get("summary") or "").strip()
    if title and summary:
        return f"{fact_type}: {title}. {summary}"
    if title:
        return f"{fact_type}: {title}"
    if summary:
        return f"{fact_type}: {summary}"
    return fact_type


def _language_keywords(texts: list[str], *, want_cjk: bool) -> list[str]:
    keywords = []
    seen = set()
    for text in texts:
        value = str(text or "").strip()
        if not value:
            continue
        if want_cjk != _contains_cjk(value):
            continue
        if value in seen:
            continue
        seen.add(value)
        keywords.append(value)
    return keywords[:6]


def extract_terms(texts: list[str]) -> list[str]:
    counter: Counter[str] = Counter()
    ordered: dict[str, str] = {}
    for text in texts:
        for raw_token in _tokenize(text):
            normalized = _normalize_term(raw_token)
            if not normalized or normalized in _GENERIC_TERMS:
                continue
            counter[normalized] += 1
            ordered.setdefault(normalized, raw_token.strip())
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [ordered[normalized] for normalized, _ in ranked[:8]]


def normalized_terms(texts: list[str]) -> list[str]:
    results = []
    seen = set()
    for text in texts:
        for raw_token in _tokenize(text):
            normalized = _normalize_term(raw_token)
            if not normalized or normalized in _GENERIC_TERMS or normalized in seen:
                continue
            seen.add(normalized)
            results.append(normalized)
    return results


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    ascii_tokens = re.findall(r"[A-Za-z][A-Za-z0-9&+/-]{2,}", text)
    cjk_tokens = re.findall(r"[\u4e00-\u9fff]{2,12}", text)
    return [*ascii_tokens, *cjk_tokens]


def _normalize_term(term: str) -> str:
    token = term.strip().lower()
    token = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", token)
    token = " ".join(token.split())
    if len(token) < 2:
        return ""
    return token


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _source_item_id(*, prefix: str, components: list[str]) -> str:
    digest = hashlib.sha256("|".join(components).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}".upper()


def _quote_sentiment(change_percent: Any) -> str | None:
    if not isinstance(change_percent, int | float):
        return None
    if change_percent >= 3:
        return "positive"
    if change_percent <= -3:
        return "negative"
    return "mixed"


def _valuation_sentiment(pressure: str) -> str | None:
    if pressure == "discounted":
        return "positive"
    if pressure == "elevated":
        return "negative"
    return "mixed"


def _financial_sentiment(metric: dict[str, Any]) -> str | None:
    revenue_yoy = metric.get("revenue_yoy")
    profit_yoy = metric.get("parent_net_profit_yoy")
    if isinstance(revenue_yoy, int | float) and isinstance(profit_yoy, int | float):
        if revenue_yoy > 0 and profit_yoy > 0:
            return "positive"
        if revenue_yoy < 0 and profit_yoy < 0:
            return "negative"
    return "mixed"
