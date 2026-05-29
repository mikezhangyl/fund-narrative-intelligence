from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any


def build_portfolio_narrative_workspace(
    *,
    payload: dict[str, Any],
    as_of: str | None = None,
    alert_threshold: float = 0.10,
    concentration_threshold: float = 0.35,
) -> dict[str, Any]:
    generated_at = as_of or _utc_now()
    watchlists = _watchlists(payload.get("watchlists"))
    current_snapshots = _snapshot_index(payload.get("current_snapshots"))
    previous_snapshots = _snapshot_index(payload.get("previous_snapshots"))
    dashboard_snapshots = [
        _dashboard_snapshot(
            watchlist=watchlist,
            snapshot=current_snapshots.get(watchlist["watchlist_id"], {}),
        )
        for watchlist in watchlists
    ]
    comparisons = [
        _comparison(
            watchlist_id=watchlist["watchlist_id"],
            previous=previous_snapshots.get(watchlist["watchlist_id"], {}),
            current=current_snapshots.get(watchlist["watchlist_id"], {}),
        )
        for watchlist in watchlists
    ]
    radar_impacts = _radar_impacts(
        radar_narratives=_list(payload.get("radar_narratives")),
        dashboard_snapshots=dashboard_snapshots,
    )
    alerts = _alerts(
        comparisons=comparisons,
        dashboard_snapshots=dashboard_snapshots,
        radar_impacts=radar_impacts,
        alert_threshold=alert_threshold,
        concentration_threshold=concentration_threshold,
    )
    validation_warning_count = sum(len(watchlist["validation_warnings"]) for watchlist in watchlists)
    dominant_narrative_count = sum(
        1
        for snapshot in dashboard_snapshots
        if snapshot["concentration"]["top_narrative_id"]
    )
    return {
        "version": "portfolio-narrative-workspace-v1",
        "generated_at": generated_at,
        "workspace": {
            "workspace_id": str(payload.get("workspace_id") or "default-workspace"),
            "workspace_name": str(payload.get("workspace_name") or "Default workspace"),
        },
        "summary": {
            "watchlist_count": len(watchlists),
            "snapshot_count": len(dashboard_snapshots),
            "dominant_narrative_count": dominant_narrative_count,
            "comparison_count": len(comparisons),
            "alert_count": len(alerts),
            "radar_impact_count": len(radar_impacts),
            "validation_warning_count": validation_warning_count,
        },
        "watchlists": watchlists,
        "dashboard": {
            "snapshots": dashboard_snapshots,
            "non_advice_disclosure": _non_advice_disclosure(),
        },
        "comparisons": comparisons,
        "alerts": alerts,
        "radar_impacts": radar_impacts,
        "field_lineage": _field_lineage(),
        "source_boundaries": _source_boundaries(),
        "disclaimer": _non_advice_disclosure(),
    }


def render_html_report(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>组合叙事工作台</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>组合叙事工作台</h1>",
            '<section class="summary">',
            _html_kv("生成时间", report.get("generated_at", "")),
            _html_kv("工作台", _mapping(report.get("workspace")).get("workspace_name", "")),
            "<p>本工作台用于观察基金、ETF、自选组合的叙事暴露、质量和变化，不构成投资建议、交易策略或收益预测。</p>",
            "</section>",
            "<section>",
            "<h2>概览</h2>",
            '<div class="metrics">',
            _html_metric("观察列表", summary.get("watchlist_count", 0)),
            _html_metric("快照", summary.get("snapshot_count", 0)),
            _html_metric("主导叙事", summary.get("dominant_narrative_count", 0)),
            _html_metric("比较", summary.get("comparison_count", 0)),
            _html_metric("观察性提醒", summary.get("alert_count", 0)),
            _html_metric("雷达影响", summary.get("radar_impact_count", 0)),
            "</div>",
            "</section>",
            _watchlists_section(report.get("watchlists")),
            _snapshots_section(_mapping(report.get("dashboard")).get("snapshots")),
            _comparisons_section(report.get("comparisons")),
            _alerts_section(report.get("alerts")),
            _radar_section(report.get("radar_impacts")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _watchlists(value: Any) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(_list(value), start=1):
        raw = _mapping(item)
        instruments, warnings = _instruments(raw.get("instruments"))
        watchlist_id = str(raw.get("watchlist_id") or f"watchlist-{index}")
        rows.append(
            {
                "watchlist_id": watchlist_id,
                "name": str(raw.get("name") or watchlist_id),
                "type": str(raw.get("type") or "fund_set"),
                "notes": str(raw.get("notes") or ""),
                "instruments": instruments,
                "validation_state": "degraded" if warnings else "valid",
                "validation_warnings": warnings,
                "latest_snapshot_id": str(raw.get("latest_snapshot_id") or ""),
            }
        )
    return rows


def _instruments(value: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows = []
    warnings = []
    for index, item in enumerate(_list(value), start=1):
        raw = _mapping(item)
        symbol = str(raw.get("symbol") or "").strip()
        kind = str(raw.get("kind") or "fund").strip()
        weight = _rounded(_float(raw.get("weight")))
        if not symbol:
            warnings.append(
                {
                    "field": f"instruments[{index}].symbol",
                    "reason": "missing_symbol",
                }
            )
            continue
        if weight < 0:
            warnings.append(
                {
                    "field": f"instruments[{index}].weight",
                    "reason": "negative_weight",
                }
            )
            continue
        rows.append({"symbol": symbol, "kind": kind, "weight": weight})
    return rows, warnings


def _dashboard_snapshot(*, watchlist: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    exposures = sorted(
        [_exposure_row(item) for item in _list(snapshot.get("exposures"))],
        key=lambda item: (-_float(item.get("raw_exposure")), str(item.get("narrative_id"))),
    )
    top = exposures[0] if exposures else {}
    trust_states = {"trusted": 0, "candidate": 0, "blocked": 0}
    for exposure in exposures:
        trust_state = str(exposure.get("trust_state") or "candidate")
        if trust_state not in trust_states:
            trust_states[trust_state] = 0
        trust_states[trust_state] += 1
    return {
        "watchlist_id": watchlist["watchlist_id"],
        "watchlist_name": watchlist["name"],
        "snapshot_id": str(snapshot.get("snapshot_id") or ""),
        "as_of": str(snapshot.get("as_of") or ""),
        "instrument_count": len(watchlist["instruments"]),
        "exposures": exposures,
        "concentration": {
            "top_narrative_id": str(top.get("narrative_id") or ""),
            "top_narrative_name": str(top.get("narrative_name") or ""),
            "top_exposure": _rounded(_float(top.get("raw_exposure"))),
        },
        "quality_breakdown": trust_states,
        "source_diagnostics": [_mapping(item) for item in _list(snapshot.get("source_diagnostics"))],
    }


def _exposure_row(item: Any) -> dict[str, Any]:
    raw = _mapping(item)
    return {
        "narrative_id": str(raw.get("narrative_id") or ""),
        "narrative_name": str(raw.get("narrative_name") or raw.get("display_name") or ""),
        "raw_exposure": _rounded(_float(raw.get("raw_exposure"))),
        "trust_state": str(raw.get("trust_state") or "candidate"),
        "quality_grade": str(raw.get("quality_grade") or ""),
        "quality_score": _rounded(_float(raw.get("quality_score"))),
        "holdings": [_mapping(holding) for holding in _list(raw.get("holdings"))],
        "evidence_ids": [str(evidence_id) for evidence_id in _list(raw.get("evidence_ids"))],
    }


def _comparison(
    *,
    watchlist_id: str,
    previous: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    previous_index = _exposure_index(previous)
    current_index = _exposure_index(current)
    narrative_ids = sorted(set(previous_index) | set(current_index))
    deltas = [
        _delta_row(
            narrative_id=narrative_id,
            previous=previous_index.get(narrative_id),
            current=current_index.get(narrative_id),
        )
        for narrative_id in narrative_ids
    ]
    return {
        "watchlist_id": watchlist_id,
        "previous_snapshot_id": str(previous.get("snapshot_id") or ""),
        "current_snapshot_id": str(current.get("snapshot_id") or ""),
        "narrative_deltas": sorted(
            deltas,
            key=lambda item: (
                1 if not item.get("current_trust_state") else 0,
                -abs(_float(item.get("delta"))),
                str(item.get("narrative_id")),
            ),
        ),
    }


def _delta_row(
    *,
    narrative_id: str,
    previous: dict[str, Any] | None,
    current: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = current or previous or {}
    previous_exposure = _float(previous.get("raw_exposure")) if previous else 0.0
    current_exposure = _float(current.get("raw_exposure")) if current else 0.0
    return {
        "narrative_id": narrative_id,
        "narrative_name": str(payload.get("narrative_name") or narrative_id),
        "previous_exposure": _rounded(previous_exposure),
        "current_exposure": _rounded(current_exposure),
        "delta": _rounded(current_exposure - previous_exposure),
        "previous_trust_state": str(previous.get("trust_state") if previous else ""),
        "current_trust_state": str(current.get("trust_state") if current else ""),
        "previous_quality_grade": str(previous.get("quality_grade") if previous else ""),
        "current_quality_grade": str(current.get("quality_grade") if current else ""),
    }


def _radar_impacts(
    *,
    radar_narratives: list[Any],
    dashboard_snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for radar in radar_narratives:
        raw = _mapping(radar)
        if str(raw.get("trend") or "").lower() != "heating":
            continue
        narrative_id = str(raw.get("narrative_id") or "")
        affected = []
        for snapshot in dashboard_snapshots:
            for exposure in _list(snapshot.get("exposures")):
                if exposure.get("narrative_id") != narrative_id:
                    continue
                affected.append(
                    {
                        "watchlist_id": snapshot["watchlist_id"],
                        "watchlist_name": snapshot["watchlist_name"],
                        "raw_exposure": exposure["raw_exposure"],
                        "trust_state": exposure["trust_state"],
                        "quality_grade": exposure["quality_grade"],
                        "holdings": exposure["holdings"],
                        "evidence_ids": exposure["evidence_ids"],
                    }
                )
        rows.append(
            {
                "narrative_id": narrative_id,
                "narrative_name": str(raw.get("narrative_name") or narrative_id),
                "heat_score": _rounded(_float(raw.get("heat_score"))),
                "trend": "heating",
                "evidence_ids": [str(item) for item in _list(raw.get("evidence_ids"))],
                "affected_watchlist_count": len(affected),
                "affected_watchlists": affected,
            }
        )
    return sorted(rows, key=lambda item: (-_float(item.get("heat_score")), str(item.get("narrative_id"))))


def _alerts(
    *,
    comparisons: list[dict[str, Any]],
    dashboard_snapshots: list[dict[str, Any]],
    radar_impacts: list[dict[str, Any]],
    alert_threshold: float,
    concentration_threshold: float,
) -> list[dict[str, Any]]:
    alerts = []
    for comparison in comparisons:
        watchlist_id = comparison["watchlist_id"]
        for delta in comparison["narrative_deltas"]:
            if not delta.get("current_trust_state"):
                continue
            previous_exposure = _float(delta.get("previous_exposure"))
            current_exposure = _float(delta.get("current_exposure"))
            if previous_exposure < concentration_threshold <= current_exposure:
                alerts.append(_alert("dominant_narrative_added", watchlist_id, delta))
            if abs(_float(delta.get("delta"))) >= alert_threshold:
                alerts.append(_alert("large_exposure_change", watchlist_id, delta))
            if _is_quality_degradation(delta):
                alerts.append(_alert("quality_degradation", watchlist_id, delta))
    for impact in radar_impacts:
        if _float(impact.get("affected_watchlist_count")) <= 0:
            continue
        alerts.append(
            {
                "alert_type": "heating_radar_overlap",
                "rule_id": "radar-overlap-v1",
                "narrative_id": impact["narrative_id"],
                "narrative_name": impact["narrative_name"],
                "affected_watchlist_count": impact["affected_watchlist_count"],
                "trigger_reason": "Heating radar narrative overlaps watched holdings.",
                "source_diagnostics": _source_diagnostics_for_impact(impact, dashboard_snapshots),
                "non_advice_disclosure": _non_advice_disclosure(),
            }
        )
    return _dedupe_alerts(alerts)


def _alert(alert_type: str, watchlist_id: str, delta: dict[str, Any]) -> dict[str, Any]:
    return {
        "alert_type": alert_type,
        "rule_id": f"{alert_type}-v1",
        "watchlist_id": watchlist_id,
        "narrative_id": delta["narrative_id"],
        "narrative_name": delta["narrative_name"],
        "previous_value": delta["previous_exposure"],
        "current_value": delta["current_exposure"],
        "delta": delta["delta"],
        "trigger_reason": _alert_reason(alert_type),
        "source_diagnostics": [],
        "non_advice_disclosure": _non_advice_disclosure(),
    }


def _alert_reason(alert_type: str) -> str:
    return {
        "dominant_narrative_added": "Narrative crossed the dominant exposure threshold.",
        "large_exposure_change": "Narrative exposure changed beyond the configured threshold.",
        "quality_degradation": "Narrative trust or quality status weakened.",
    }.get(alert_type, "Observational workspace alert.")


def _is_quality_degradation(delta: dict[str, Any]) -> bool:
    previous_trust = str(delta.get("previous_trust_state") or "")
    current_trust = str(delta.get("current_trust_state") or "")
    if previous_trust == "trusted" and current_trust and current_trust != "trusted":
        return True
    return _grade_rank(delta.get("current_quality_grade")) > _grade_rank(delta.get("previous_quality_grade"))


def _grade_rank(value: Any) -> int:
    return {"A": 1, "B": 2, "C": 3, "D": 4}.get(str(value or "").upper(), 99)


def _source_diagnostics_for_impact(
    impact: dict[str, Any],
    dashboard_snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    affected_ids = {item["watchlist_id"] for item in _list(impact.get("affected_watchlists"))}
    rows = []
    for snapshot in dashboard_snapshots:
        if snapshot["watchlist_id"] in affected_ids:
            rows.extend(_list(snapshot.get("source_diagnostics")))
    return rows


def _dedupe_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    rows = []
    for alert in alerts:
        key = (
            alert.get("alert_type"),
            alert.get("watchlist_id", ""),
            alert.get("narrative_id", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(alert)
    return rows


def _exposure_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["narrative_id"]: row
        for row in (_exposure_row(item) for item in _list(snapshot.get("exposures")))
        if row["narrative_id"]
    }


def _snapshot_index(value: Any) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("watchlist_id")): _mapping(item)
        for item in _list(value)
        if str(_mapping(item).get("watchlist_id") or "")
    }


def _field_lineage() -> dict[str, dict[str, str]]:
    return {
        "watchlists": {
            "owner_service": "FNI",
            "source_service": "FNI",
            "contract": "workspace-entity-watchlist-v1",
        },
        "dashboard.snapshots.exposures": {
            "owner_service": "FNI",
            "source_service": "Narrative Service",
            "contract": "narrative-exposure-snapshot-v1",
        },
        "dashboard.snapshots.holdings": {
            "owner_service": "Gateway",
            "source_service": "Gateway",
            "contract": "fund-holdings-v1",
        },
        "radar_impacts": {
            "owner_service": "FNI",
            "source_service": "Narrative Service",
            "contract": "narrative-radar-v1",
        },
        "alerts": {
            "owner_service": "FNI",
            "source_service": "FNI",
            "contract": "observational-alert-v1",
        },
    }


def _source_boundaries() -> dict[str, str]:
    return {
        "Gateway": "fund holdings, instruments, and market data",
        "Narrative Service": "radar, evidence quality, trust state, and evidence ids",
        "FNI": "workspace aggregation, comparisons, alerts, reports, and artifacts",
    }


def _non_advice_disclosure() -> str:
    return (
        "Observational narrative monitoring only; not investment advice, "
        "trading guidance, price prediction, or automatic decisioning."
    )


def _watchlists_section(value: Any) -> str:
    return _rows_section(
        "观察列表",
        value,
        (
            ("watchlist_id", "ID"),
            ("name", "名称"),
            ("type", "类型"),
            ("validation_state", "状态"),
            ("validation_warnings", "校验提示"),
        ),
    )


def _snapshots_section(value: Any) -> str:
    rows = []
    for snapshot in _list(value):
        concentration = _mapping(snapshot.get("concentration"))
        rows.append(
            {
                "watchlist_name": snapshot.get("watchlist_name"),
                "top_narrative": concentration.get("top_narrative_name"),
                "top_exposure": concentration.get("top_exposure"),
                "quality_breakdown": snapshot.get("quality_breakdown"),
            }
        )
    return _rows_section(
        "叙事暴露仪表盘",
        rows,
        (
            ("watchlist_name", "观察列表"),
            ("top_narrative", "主导叙事"),
            ("top_exposure", "主导暴露"),
            ("quality_breakdown", "质量拆分"),
        ),
    )


def _comparisons_section(value: Any) -> str:
    rows = []
    for comparison in _list(value):
        for delta in _list(_mapping(comparison).get("narrative_deltas"))[:5]:
            rows.append({"watchlist_id": comparison.get("watchlist_id"), **_mapping(delta)})
    return _rows_section(
        "暴露变化比较",
        rows,
        (
            ("watchlist_id", "观察列表"),
            ("narrative_name", "叙事"),
            ("previous_exposure", "前值"),
            ("current_exposure", "现值"),
            ("delta", "变化"),
        ),
    )


def _alerts_section(value: Any) -> str:
    return _rows_section(
        "观察性提醒",
        value,
        (
            ("alert_type", "类型"),
            ("watchlist_id", "观察列表"),
            ("narrative_name", "叙事"),
            ("trigger_reason", "触发原因"),
        ),
    )


def _radar_section(value: Any) -> str:
    return _rows_section(
        "雷达到组合影响",
        value,
        (
            ("narrative_id", "叙事 ID"),
            ("narrative_name", "叙事"),
            ("heat_score", "热度"),
            ("affected_watchlist_count", "影响列表数"),
        ),
    )


def _rows_section(
    title: str,
    value: Any,
    columns: tuple[tuple[str, str], ...],
) -> str:
    rows = [_mapping(row) for row in _list(value)]
    if not rows:
        return f"<section><h2>{_html_text(title)}</h2><p class=\"empty\">没有返回可展示数据。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{_html_text(_cell(row.get(key)))}</td>" for key, _ in columns)
        + "</tr>"
        for row in rows
    )
    return f"<section><h2>{_html_text(title)}</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_html_text(label)}</span><strong>{_html_text(value)}</strong></div>'


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 28px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.metric { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 12px; }
.metric span { display: block; color: #52606d; font-size: 13px; }
.metric strong { display: block; margin-top: 6px; font-size: 22px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
.empty { color: #52606d; }
"""


def _cell(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value or "")


def _html_text(value: Any) -> str:
    return escape(_cell(value), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _rounded(value: float) -> float:
    return round(value, 4)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
