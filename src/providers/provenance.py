from __future__ import annotations

from typing import Any

MOCK_PROVIDER_NAME = "mock-fixture-provider"
MOCK_PROVIDER_VERSION = "mock-v1"

PROVIDER_LAYERS = (
    "holdings",
    "narrative_registry",
    "stock_mappings",
    "evidence",
    "signals",
)

LAYER_DISPLAY_NAMES = {
    "holdings": "Holdings",
    "narrative_registry": "Narrative Registry",
    "stock_mappings": "Stock Mappings",
    "evidence": "Evidence",
    "signals": "Signals",
    "announcements": "Announcements",
    "market_quotes": "Market Quotes",
    "derived_signals": "Derived Signals",
}


def build_mock_provider_foundation(
    layers: dict[str, dict[str, Any]] | None = None,
    degradation_events: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return build_provider_foundation(
        layers=layers or {layer: mock_layer(layer) for layer in PROVIDER_LAYERS},
        degradation_events=degradation_events or [],
    )


def build_provider_foundation(
    layers: dict[str, dict[str, Any]],
    degradation_events: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    layer_order = [
        *PROVIDER_LAYERS,
        *(layer for layer in layers if layer not in PROVIDER_LAYERS),
    ]
    normalized_layers = {
        layer: _normalize_layer(layer, layers[layer]) for layer in layer_order
    }
    events = degradation_events or []
    effective_data_quality = _effective_data_quality(normalized_layers)
    disclosure_required = (
        effective_data_quality != "fresh"
        or any(layer["is_mock"] for layer in normalized_layers.values())
        or bool(events)
    )
    return {
        "effective_data_quality": effective_data_quality,
        "disclosure_required": disclosure_required,
        "disclosure_message": _disclosure_message(
            layers=normalized_layers,
            effective_data_quality=effective_data_quality,
            degradation_events=events,
        ),
        "layers": normalized_layers,
        "degradation_events": events,
    }


def layer_from_provider_metadata(
    layer: str,
    provider_metadata: dict[str, Any],
    note: str,
) -> dict[str, Any]:
    provider_name = str(provider_metadata["provider_name"])
    data_quality = str(provider_metadata["data_quality"])
    return {
        "layer": layer,
        "provider_name": provider_name,
        "provider_version": str(provider_metadata["provider_version"]),
        "data_quality": data_quality,
        "source_url": provider_metadata.get("source_url"),
        "is_mock": _is_mock(provider_name=provider_name, data_quality=data_quality),
        "note": note,
    }


def mock_layer(
    layer: str,
    note: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    return {
        "layer": layer,
        "provider_name": MOCK_PROVIDER_NAME,
        "provider_version": MOCK_PROVIDER_VERSION,
        "data_quality": "mock",
        "source_url": source_url or f"mock://fixtures/{layer}",
        "is_mock": True,
        "note": note or "V1 Mock fixture layer.",
    }


def _normalize_layer(layer: str, payload: dict[str, Any]) -> dict[str, Any]:
    provider_name = str(payload["provider_name"])
    data_quality = str(payload["data_quality"])
    return {
        "layer": layer,
        "display_name": LAYER_DISPLAY_NAMES.get(layer, layer.replace("_", " ").title()),
        "provider_name": provider_name,
        "provider_version": str(payload["provider_version"]),
        "data_quality": data_quality,
        "source_url": payload.get("source_url"),
        "is_mock": bool(payload.get("is_mock"))
        or _is_mock(provider_name=provider_name, data_quality=data_quality),
        "note": str(payload.get("note") or ""),
    }


def _effective_data_quality(layers: dict[str, dict[str, Any]]) -> str:
    qualities = [layer["data_quality"] for layer in layers.values()]
    if all(quality == "fresh" for quality in qualities):
        return "fresh"
    if all(quality == "mock" for quality in qualities):
        return "mock"
    if all(quality == "unavailable" for quality in qualities):
        return "unavailable"
    return "partial"


def _disclosure_message(
    layers: dict[str, dict[str, Any]],
    effective_data_quality: str,
    degradation_events: list[dict[str, str]],
) -> str:
    mock_layers = [
        layer["display_name"] for layer in layers.values() if layer["is_mock"]
    ]
    live_layers = [
        f"{layer['display_name']} 来自 {_display_provider(layer['provider_name'])}"
        for layer in layers.values()
        if not layer["is_mock"]
    ]

    if effective_data_quality == "mock":
        base = "Mock 数据：本报告使用 V1 Mock fixtures，不代表完整真实环境输出。"
    elif mock_layers:
        live_summary = "；".join(live_layers) if live_layers else "部分数据来自真实 provider"
        mock_summary = "、".join(mock_layers)
        base = (
            f"混合数据源：{live_summary}；{mock_summary} 使用 Mock fixtures。"
            "请勿将该报告视为完整真实环境输出。"
        )
    else:
        base = "数据源为真实 provider，但仍仅用于叙事分析，不构成投资建议。"

    if degradation_events:
        event_types = ", ".join(
            sorted({event.get("type", "unknown") for event in degradation_events})
        )
        return f"{base} 降级事件：{event_types}。"
    return base


def _display_provider(provider_name: str) -> str:
    if provider_name.startswith("eastmoney"):
        return "Eastmoney"
    if provider_name.startswith("cninfo"):
        return "CNINFO"
    if provider_name.startswith("mock"):
        return "Mock fixtures"
    return provider_name


def _is_mock(provider_name: str, data_quality: str) -> bool:
    return provider_name.startswith("mock") or data_quality == "mock"
