from __future__ import annotations

from typing import Any

from src.validation import validate_valuation_snapshot_payload

QUOTE_DERIVED_VALUATION_PROVIDER = "quote-derived-valuation"
QUOTE_DERIVED_VALUATION_VERSION = "quote-derived-valuation-v1"
QUOTE_DERIVED_VALUATION_SOURCE_URL = "derived://market-quotes/valuation-context"


def build_quote_derived_valuation_snapshots(
    market_quotes_payload: dict[str, Any],
) -> dict[str, Any]:
    quotes = market_quotes_payload.get("quotes")
    if not isinstance(quotes, list):
        quotes = []
    payload = {
        "version": "valuation-snapshot-v1",
        "provider_name": QUOTE_DERIVED_VALUATION_PROVIDER,
        "provider_version": QUOTE_DERIVED_VALUATION_VERSION,
        "data_quality": str(market_quotes_payload.get("data_quality") or "unavailable"),
        "source_url": QUOTE_DERIVED_VALUATION_SOURCE_URL,
        "retrieved_at": str(market_quotes_payload.get("retrieved_at") or ""),
        "valuation_basis": "quote_derived_context",
        "valuations": [_valuation_from_quote(quote) for quote in quotes],
        "missing_stock_codes": list(market_quotes_payload.get("missing_stock_codes") or []),
    }
    validate_valuation_snapshot_payload(payload)
    return payload


def valuation_provider_layer(payload: dict[str, Any]) -> dict[str, Any]:
    validate_valuation_snapshot_payload(payload)
    return {
        "layer": "valuation",
        "provider_name": str(payload["provider_name"]),
        "provider_version": str(payload["provider_version"]),
        "data_quality": str(payload["data_quality"]),
        "source_url": str(payload["source_url"]),
        "is_mock": payload["data_quality"] == "mock",
        "note": _valuation_layer_note(str(payload["valuation_basis"])),
    }


def _valuation_layer_note(valuation_basis: str) -> str:
    if valuation_basis == "provider_valuation_metrics":
        return (
            "Eastmoney valuation metrics; not a full financial statement or "
            "historical percentile valuation feed."
        )
    return "Quote-derived valuation context; not a full fundamental valuation feed."


def _valuation_from_quote(quote: dict[str, Any]) -> dict[str, Any]:
    change_percent = _optional_float(quote.get("change_percent"))
    return {
        "stock_code": str(quote.get("stock_code") or ""),
        "stock_name": str(quote.get("stock_name") or ""),
        "latest_price": _optional_float(quote.get("latest_price")),
        "previous_close": _optional_float(quote.get("previous_close")),
        "price_change_percent": change_percent,
        "valuation_pressure": _valuation_pressure(change_percent),
        "source": "market_quote",
        "source_provider": str(quote.get("source_provider") or ""),
        "source_url": quote.get("source_url"),
        "retrieved_at": quote.get("retrieved_at"),
    }


def _valuation_pressure(change_percent: float | None) -> str:
    if change_percent is None:
        return "unknown"
    if change_percent >= 5:
        return "elevated"
    if change_percent <= -5:
        return "discounted"
    return "neutral"


def _optional_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
