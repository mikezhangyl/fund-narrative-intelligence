from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from html import escape
from typing import Any, Callable
from urllib.request import Request, urlopen

from src.scanners.source_event_schema import validate_source_event

SEC_EDGAR_PROVIDER_NAME = "sec-edgar-submissions"
SEC_EDGAR_PROVIDER_VERSION = "sec-edgar-submissions-v1"
SEC_EDGAR_SUBMISSIONS_BASE_URL = "https://data.sec.gov/submissions"
SEC_ARCHIVES_BASE_URL = "https://www.sec.gov/Archives/edgar/data"
DEFAULT_SEC_USER_AGENT = "fund-narrative-intelligence local research; set SEC_EDGAR_USER_AGENT for contact"

SecEdgarFetcher = Callable[[str, dict[str, str]], dict[str, Any]]


class SecEdgarSubmissionsProvider:
    provider_name = SEC_EDGAR_PROVIDER_NAME
    provider_version = SEC_EDGAR_PROVIDER_VERSION
    source_url = SEC_EDGAR_SUBMISSIONS_BASE_URL

    def __init__(
        self,
        *,
        fetcher: SecEdgarFetcher | None = None,
        user_agent: str = DEFAULT_SEC_USER_AGENT,
    ) -> None:
        self.fetcher = fetcher or _fetch_sec_json
        self.user_agent = user_agent

    def get_submissions(
        self,
        *,
        cik: str,
        ticker: str = "",
        company_name: str = "",
        limit: int = 20,
        fetched_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_cik = normalize_cik(cik)
        retrieved_at = fetched_at or _utc_now()
        fetch_url = f"{self.source_url}/CIK{normalized_cik}.json"
        try:
            raw_payload = self.fetcher(fetch_url, _headers(self.user_agent))
        except Exception as exc:
            return _degraded_payload(
                cik=normalized_cik,
                ticker=ticker,
                company_name=company_name,
                fetch_url=fetch_url,
                fetched_at=retrieved_at,
                reason=f"SEC EDGAR submissions fetch failed for {normalized_cik}: {exc}",
            )

        resolved_ticker = ticker or _first_string(raw_payload.get("tickers"))
        resolved_company_name = company_name or str(raw_payload.get("name") or "")
        events, skipped_count = sec_submissions_to_source_events(
            raw_payload=raw_payload,
            cik=normalized_cik,
            ticker=resolved_ticker,
            company_name=resolved_company_name,
            fetched_at=retrieved_at,
            limit=limit,
        )
        return {
            "version": SEC_EDGAR_PROVIDER_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "source_url": fetch_url,
            "fetched_at": retrieved_at,
            "data_quality": "fresh" if events else "unavailable",
            "source_trust_tier": "trusted_fact",
            "evidence_granularity": "metadata_only",
            "summary": {
                "requested_cik": normalized_cik,
                "event_count": len(events),
                "skipped_filing_count": skipped_count,
                "degradation_count": 0,
            },
            "events": events,
            "degradation_events": [],
        }


def sec_submissions_to_source_events(
    *,
    raw_payload: dict[str, Any],
    cik: str,
    ticker: str,
    company_name: str,
    fetched_at: str,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = _recent_filing_rows(raw_payload)
    events = []
    skipped_count = 0
    for row in rows[: max(0, limit)]:
        if not row.get("accession_number") or not row.get("form_type"):
            skipped_count += 1
            continue
        events.append(
            _source_event_from_filing_row(
                row,
                cik=cik,
                ticker=ticker,
                company_name=company_name,
                fetched_at=fetched_at,
            )
        )
    return events, skipped_count


def render_sec_edgar_smoke_html(payload: dict[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>SEC EDGAR 官方披露事件</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>SEC EDGAR 官方披露事件</h1>",
            '<section class="summary">',
            "<p>来源为 SEC EDGAR submissions JSON；本切片只归一化披露 metadata，不解析全文或 XBRL，不给交易解释。</p>",
            _html_kv("CIK", summary.get("requested_cik", "")),
            _html_kv("事件数", summary.get("event_count", 0)),
            _html_kv("跳过记录", summary.get("skipped_filing_count", 0)),
            _html_kv("数据质量", payload.get("data_quality", "")),
            _html_kv("信任层级", payload.get("source_trust_tier", "")),
            _html_kv("证据粒度", payload.get("evidence_granularity", "")),
            "</section>",
            _events_table(_list(payload.get("events"))),
            _degradation_table(_list(payload.get("degradation_events"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def normalize_cik(value: str) -> str:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        raise ValueError("SEC CIK must contain digits")
    return digits.zfill(10)[-10:]


def _source_event_from_filing_row(
    row: dict[str, str],
    *,
    cik: str,
    ticker: str,
    company_name: str,
    fetched_at: str,
) -> dict[str, Any]:
    accession = row["accession_number"]
    form_type = row["form_type"]
    filing_date = row.get("filing_date", "")
    source_url = _filing_index_url(cik=cik, accession_number=accession)
    raw_hash = _raw_hash(row)
    event = validate_source_event(
        {
            "event_id": _stable_id("EVT_SEC_EDGAR", [cik, accession, form_type]),
            "source_type": "filing",
            "provider": SEC_EDGAR_PROVIDER_NAME,
            "provider_version": SEC_EDGAR_PROVIDER_VERSION,
            "source_url": source_url,
            "event_time": filing_date,
            "title": f"{ticker or cik} {form_type} SEC filing {filing_date}".strip(),
            "summary": (
                f"{company_name or ticker or cik} filed {form_type} on SEC EDGAR. "
                "This event is metadata_only; no filing text or XBRL facts were parsed."
            ),
            "stock_codes": [ticker] if ticker else [],
            "mentioned_stocks": [
                {"stock_code": ticker, "stock_name": company_name}
            ]
            if ticker
            else [],
            "narrative_hints": _narrative_hints(form_type),
            "evidence_claims": [
                f"SEC EDGAR filing metadata reports form {form_type} with accession {accession}."
            ],
            "source_metadata": {
                "provider": SEC_EDGAR_PROVIDER_NAME,
                "provider_version": SEC_EDGAR_PROVIDER_VERSION,
                "permission_status": "public_api",
                "degradation_state": "ok",
                "source_mode": "external_contract",
                "cik": cik,
                "ticker": ticker,
                "company_name": company_name,
                "form_type": form_type,
                "event_class": _event_class(form_type),
                "filing_date": filing_date,
                "report_date": row.get("report_date", ""),
                "accession_number": accession,
                "primary_document": row.get("primary_document", ""),
                "primary_doc_description": row.get("primary_doc_description", ""),
                "fetched_at": fetched_at,
                "raw_hash": raw_hash,
                "source_trust_tier": "trusted_fact",
                "evidence_granularity": "metadata_only",
            },
        }
    )
    return {
        **event,
        "source_trust_tier": "trusted_fact",
        "evidence_granularity": "metadata_only",
    }


def _recent_filing_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    recent = _mapping(_mapping(payload.get("filings")).get("recent"))
    accession_numbers = _strings(recent.get("accessionNumber"))
    filing_dates = _strings(recent.get("filingDate"))
    report_dates = _strings(recent.get("reportDate"))
    forms = _strings(recent.get("form"))
    primary_documents = _strings(recent.get("primaryDocument"))
    descriptions = _strings(recent.get("primaryDocDescription"))
    rows = []
    for index, accession in enumerate(accession_numbers):
        rows.append(
            {
                "accession_number": accession,
                "filing_date": _at(filing_dates, index),
                "report_date": _at(report_dates, index),
                "form_type": _at(forms, index),
                "primary_document": _at(primary_documents, index),
                "primary_doc_description": _at(descriptions, index),
            }
        )
    return rows


def _event_class(form_type: str) -> str:
    normalized = form_type.upper().strip()
    if normalized == "8-K":
        return "current_report"
    if normalized == "10-K":
        return "annual_report"
    if normalized == "10-Q":
        return "quarterly_report"
    if normalized == "6-K":
        return "foreign_report"
    if normalized in {"3", "4", "5"} or normalized.startswith(("SC 13", "13D", "13G")):
        return "insider_ownership"
    return "other_filing"


def _narrative_hints(form_type: str) -> list[str]:
    event_class = _event_class(form_type)
    return {
        "current_report": ["official filing", "current report", "material event"],
        "annual_report": ["official filing", "annual report", "business update"],
        "quarterly_report": ["official filing", "quarterly report", "business update"],
        "foreign_report": ["official filing", "foreign issuer report"],
        "insider_ownership": ["official filing", "ownership disclosure"],
    }.get(event_class, ["official filing"])


def _degraded_payload(
    *,
    cik: str,
    ticker: str,
    company_name: str,
    fetch_url: str,
    fetched_at: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "version": SEC_EDGAR_PROVIDER_VERSION,
        "provider_name": SEC_EDGAR_PROVIDER_NAME,
        "provider_version": SEC_EDGAR_PROVIDER_VERSION,
        "source_url": fetch_url,
        "fetched_at": fetched_at,
        "data_quality": "unavailable",
        "source_trust_tier": "trusted_fact",
        "evidence_granularity": "metadata_only",
        "summary": {
            "requested_cik": cik,
            "event_count": 0,
            "skipped_filing_count": 0,
            "degradation_count": 1,
        },
        "events": [],
        "degradation_events": [
            {
                "type": "provider_unavailable",
                "provider_name": SEC_EDGAR_PROVIDER_NAME,
                "reason": reason,
            }
        ],
        "request_context": {
            "ticker": ticker,
            "company_name": company_name,
        },
    }


def _fetch_sec_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _headers(user_agent: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": user_agent,
    }


def _filing_index_url(*, cik: str, accession_number: str) -> str:
    cik_int = str(int(cik))
    accession_no_dash = accession_number.replace("-", "")
    return f"{SEC_ARCHIVES_BASE_URL}/{cik_int}/{accession_no_dash}/{accession_number}-index.html"


def _raw_hash(row: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1(
        "|".join(str(value or "") for value in values).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16].upper()}"


def _events_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>披露事件</h2><p>没有可展示事件。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("日期", "表单", "事件类型", "公司", "Accession", "Trust", "URL")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('event_time'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('form_type'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('event_class'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('company_name'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('accession_number'))}</td>"
        f"<td>{_html_text(row.get('source_trust_tier'))}</td>"
        f"<td>{_html_text(row.get('source_url'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>披露事件</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


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


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _at(values: list[str], index: int) -> str:
    return values[index] if index < len(values) else ""


def _first_string(value: Any) -> str:
    strings = _strings(value)
    return strings[0] if strings else ""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
