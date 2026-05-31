from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from html import escape
from typing import Any, Callable
from urllib.request import Request, urlopen

from src.scanners.source_event_schema import validate_source_event

STOCKTWITS_HEAT_SIGNAL_VERSION = "stocktwits-heat-signal-v1"
STOCKTWITS_PROVIDER_NAME = "stocktwits-symbol-stream"
STOCKTWITS_PROVIDER_VERSION = "stocktwits-symbol-stream-v1"
STOCKTWITS_SYMBOL_STREAM_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"

StocktwitsFetcher = Callable[[str, int], dict[str, Any]]


class StocktwitsHeatSignalProvider:
    provider_name = STOCKTWITS_PROVIDER_NAME
    provider_version = STOCKTWITS_PROVIDER_VERSION

    def __init__(
        self,
        *,
        fetcher: StocktwitsFetcher | None = None,
        timeout_seconds: int = 10,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self.fetcher = fetcher or _fetch_json
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds

    def get_heat_signals(
        self,
        *,
        symbols: list[str],
        limit: int = 5,
        fetched_at: str | None = None,
    ) -> dict[str, Any]:
        retrieved_at = fetched_at or _utc_now()
        events: list[dict[str, Any]] = []
        degradation_events: list[dict[str, Any]] = []
        requested_symbols = [_normalize_symbol(symbol) for symbol in symbols if _normalize_symbol(symbol)]
        for symbol in requested_symbols:
            url = _stream_url(symbol=symbol, limit=limit)
            try:
                payload = self.fetcher(url, self.timeout_seconds)
            except Exception as exc:
                degradation_events.append(
                    {
                        "type": "provider_unavailable",
                        "provider_name": self.provider_name,
                        "symbol": symbol,
                        "reason": f"Stocktwits fetch failed for {symbol}: {exc}",
                    }
                )
                continue
            messages = [item for item in payload.get("messages", []) if isinstance(item, dict)]
            if not messages:
                degradation_events.append(
                    {
                        "type": "empty_response",
                        "provider_name": self.provider_name,
                        "symbol": symbol,
                        "reason": f"Stocktwits returned no messages for {symbol}",
                    }
                )
                continue
            events.extend(
                _message_to_source_event(
                    message,
                    symbol=symbol,
                    fetched_at=retrieved_at,
                )
                for message in messages[: max(0, limit)]
            )
        return {
            "version": STOCKTWITS_HEAT_SIGNAL_VERSION,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "fetched_at": retrieved_at,
            "data_quality": _data_quality(events=events, degradation_events=degradation_events),
            "heat_trust_tier": "heat_signal_only",
            "summary": {
                "requested_symbol_count": len(requested_symbols),
                "message_count": len(events),
                "degradation_count": len(degradation_events),
                "heat_trust_tier": "heat_signal_only",
            },
            "request_policy": {
                "enabled_by_default": False,
                "timeout_seconds": self.timeout_seconds,
                "cache_ttl_seconds": self.cache_ttl_seconds,
                "rate_limit_policy": "bounded_symbol_smoke_only",
            },
            "events": events,
            "degradation_events": degradation_events,
        }


def render_stocktwits_heat_signal_html(payload: dict[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>Stocktwits 热度信号试点</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>Stocktwits 热度信号试点</h1>",
            '<section class="summary">',
            "<p>Stocktwits 消息只作为 heat_signal_only 社交热度信号；不能作为 trusted evidence，不能替代官方披露或新闻事实。</p>",
            _html_kv("请求 symbol", summary.get("requested_symbol_count", 0)),
            _html_kv("消息数", summary.get("message_count", 0)),
            _html_kv("降级数", summary.get("degradation_count", 0)),
            _html_kv("信任层级", summary.get("heat_trust_tier", "")),
            "</section>",
            _events_table(_list(payload.get("events"))),
            _degradation_table(_list(payload.get("degradation_events"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _message_to_source_event(
    message: dict[str, Any],
    *,
    symbol: str,
    fetched_at: str,
) -> dict[str, Any]:
    message_id = str(message.get("id") or "")
    body = _clean_text(message.get("body"))
    created_at = _clean_text(message.get("created_at"))
    user = _mapping(message.get("user"))
    username = _clean_text(user.get("username"))
    user_id = _clean_text(user.get("id"))
    body_excerpt = _excerpt(body)
    source_url = (
        f"https://stocktwits.com/{username}/message/{message_id}"
        if username and message_id
        else ""
    )
    event = validate_source_event(
        {
            "event_id": _stable_id("EVT_STOCKTWITS", [symbol, message_id, created_at, body_excerpt]),
            "source_type": "social",
            "provider": STOCKTWITS_PROVIDER_NAME,
            "provider_version": STOCKTWITS_PROVIDER_VERSION,
            "source_url": source_url,
            "event_time": created_at,
            "title": f"{symbol} Stocktwits heat message {message_id}".strip(),
            "summary": "Stocktwits message metadata normalized as heat_signal_only; body is treated as social chatter, not fact evidence.",
            "stock_codes": [symbol],
            "mentioned_stocks": [{"stock_code": symbol, "stock_name": _symbol_title(message, symbol)}],
            "narrative_hints": [symbol, "social heat"],
            "evidence_claims": [
                f"Stocktwits message {message_id} mentions {symbol}; message content is heat-only."
            ],
            "source_metadata": {
                "provider": STOCKTWITS_PROVIDER_NAME,
                "provider_version": STOCKTWITS_PROVIDER_VERSION,
                "permission_status": "public_symbol_stream",
                "degradation_state": "ok",
                "source_mode": "external_contract",
                "symbol": symbol,
                "message_id": message_id,
                "user_id": user_id,
                "username": username,
                "body_excerpt": body_excerpt,
                "fetched_at": fetched_at,
                "heat_trust_tier": "heat_signal_only",
                "user_profiled": False,
                "historical_backfill": False,
                "raw_hash": _raw_hash(message),
            },
        }
    )
    return {
        **event,
        "heat_trust_tier": "heat_signal_only",
    }


def _fetch_json(url: str, timeout_seconds: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _stream_url(*, symbol: str, limit: int) -> str:
    return f"{STOCKTWITS_SYMBOL_STREAM_URL.format(symbol=symbol)}?limit={limit}"


def _data_quality(
    *,
    events: list[dict[str, Any]],
    degradation_events: list[dict[str, Any]],
) -> str:
    if events and degradation_events:
        return "partial"
    if events:
        return "fresh"
    if degradation_events and all(event.get("type") == "empty_response" for event in degradation_events):
        return "empty"
    return "unavailable"


def _symbol_title(message: dict[str, Any], symbol: str) -> str:
    for item in _list(message.get("symbols")):
        if str(item.get("symbol") or "").upper() == symbol:
            return _clean_text(item.get("title"))
    return ""


def _normalize_symbol(symbol: str) -> str:
    return "".join(ch for ch in str(symbol).upper().strip() if ch.isalnum() or ch in {".", "-"})


def _excerpt(value: str, max_length: int = 180) -> str:
    text = " ".join(value.split())
    return text if len(text) <= max_length else f"{text[: max_length - 1]}..."


def _raw_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _stable_id(prefix: str, values: list[Any]) -> str:
    digest = hashlib.sha1(
        "|".join(str(value or "") for value in values).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16].upper()}"


def _events_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>热度消息</h2><p>没有可展示消息。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("时间", "Symbol", "Message", "User", "Trust", "URL")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('event_time'))}</td>"
        f"<td>{_html_text(','.join(_list(row.get('stock_codes'))))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('body_excerpt'))}</td>"
        f"<td>{_html_text(_mapping(row.get('source_metadata')).get('username'))}</td>"
        f"<td>{_html_text(row.get('heat_trust_tier'))}</td>"
        f"<td>{_html_text(row.get('source_url'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>热度消息</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _degradation_table(events: list[Any]) -> str:
    rows = [_mapping(event) for event in events]
    if not rows:
        return "<section><h2>降级事件</h2><p>没有降级事件。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for label in ("类型", "Symbol", "原因"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('type'))}</td>"
        f"<td>{_html_text(row.get('symbol'))}</td>"
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


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
