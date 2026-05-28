from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any

from src.scanners.report_source_disclosure import (
    market_data_source_payload,
    source_fallback_zh,
    source_status_zh,
    source_warning_summary_zh,
)
from src.scanners.trust_state_disclosure import trust_state_display_zh


@dataclass(frozen=True)
class FundHoldingExposureConfig:
    fund_code: str
    sector_trade_date: str | None = None
    limit: int = 10
    sector_types: tuple[str, ...] = ("concept",)
    limit_per_symbol: int = 50
    sector_universe_limit: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def execute_fund_holding_exposure_report(
    *,
    data_source: Any,
    config: FundHoldingExposureConfig,
    narrative_registry: dict[str, Any],
    stock_narrative_mappings: list[dict[str, Any]],
    narrative_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    profile_rows = _safe_fetch_profile(data_source, config, failures)
    holding_rows = _safe_fetch_holdings(data_source, config, failures)
    holdings = [_holding_payload(row) for row in holding_rows]
    membership_rows = _safe_fetch_memberships(data_source, config, holdings, failures)
    industry_exposures = _industry_exposures(holdings)
    sector_exposures = _sector_exposures(holdings, membership_rows)
    narrative_source_payload = _narrative_source_payload(narrative_source)
    market_source_payload = market_data_source_payload(
        data_source=data_source,
        row_groups=[profile_rows, holding_rows, membership_rows],
        failures=failures,
    )
    narrative_exposures = _narrative_exposures(
        holdings=holdings,
        narrative_registry=narrative_registry,
        stock_narrative_mappings=stock_narrative_mappings,
    )
    data_gaps = _data_gaps(
        profile_rows=profile_rows,
        holdings=holdings,
        membership_rows=membership_rows,
        narrative_exposures=narrative_exposures,
        stock_narrative_mappings=stock_narrative_mappings,
        failures=failures,
    )
    return {
        "version": "fund-holding-exposure-v1",
        "generated_at": _utc_now(),
        "status": _status(
            holdings=holdings,
            failures=failures,
            data_gaps=data_gaps,
        ),
        "config": config.to_dict(),
        "fund": _fund_payload(config.fund_code, profile_rows),
        "intelligence_trust": _intelligence_trust(
            narrative_registry=narrative_registry,
            stock_narrative_mappings=stock_narrative_mappings,
        ),
        "summary": {
            "profile_row_count": len(profile_rows),
            "holding_count": len(holdings),
            "holding_weight_sum": _rounded(sum(item["weight"] for item in holdings)),
            "sector_membership_row_count": len(membership_rows),
            "industry_exposure_count": len(industry_exposures),
            "sector_exposure_count": len(sector_exposures),
            "narrative_exposure_count": len(narrative_exposures),
            "narrative_source": narrative_source_payload["source"],
            "data_gap_count": len(data_gaps),
        },
        "narrative_source": narrative_source_payload,
        "market_data_source": market_source_payload,
        "holdings": holdings,
        "industry_exposures": industry_exposures,
        "sector_exposures": sector_exposures,
        "narrative_exposures": narrative_exposures,
        "sector_memberships": membership_rows,
        "data_gaps": data_gaps,
        "data_gap_summary": {
            "gap_count": len(data_gaps),
            "scopes": [gap["scope"] for gap in data_gaps],
        },
        "failures": failures,
        "degradation_events": list(getattr(data_source, "degradation_events", [])),
        "disclaimer": (
            "Can-Do fund holding exposure report for observability only; not an "
            "investment recommendation, trading strategy, or prediction."
        ),
    }


def render_html_report(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    fund = _mapping(report.get("fund"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>基金持仓暴露报告</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>基金持仓暴露报告</h1>",
            '<section class="summary">',
            _html_kv("报告状态", _status_label(str(report.get("status", "")))),
            _html_kv("基金代码", fund.get("fund_code", "")),
            _html_kv("基金名称", fund.get("fund_name", "")),
            _html_kv("生成时间", report.get("generated_at", "")),
            _html_trust_notice(report.get("intelligence_trust")),
            _html_narrative_source_notice(report.get("narrative_source")),
            _html_market_data_source_notice(report.get("market_data_source")),
            "<p>本报告用于观察基金持仓的行业、板块与叙事暴露，不构成投资建议、交易策略或涨跌预测。</p>",
            "</section>",
            "<section>",
            "<h2>覆盖概览</h2>",
            '<div class="metrics">',
            _html_metric("持仓数", summary.get("holding_count", 0)),
            _html_metric("持仓权重合计", summary.get("holding_weight_sum", 0)),
            _html_metric("板块关系行数", summary.get("sector_membership_row_count", 0)),
            _html_metric("叙事暴露数", summary.get("narrative_exposure_count", 0)),
            "</div>",
            "</section>",
            _html_rows_section(
                "行业暴露",
                report.get("industry_exposures"),
                (
                    ("industry", "行业"),
                    ("raw_weight", "原始权重"),
                    ("normalized_weight", "归一权重"),
                    ("holding_count", "持仓数"),
                    ("names", "股票"),
                ),
            ),
            _html_rows_section(
                "叙事暴露",
                report.get("narrative_exposures"),
                (
                    ("narrative_name", "叙事"),
                    ("raw_exposure", "原始暴露"),
                    ("normalized_exposure", "归一暴露"),
                    ("confidence", "置信度"),
                    ("names", "股票"),
                ),
            ),
            _html_rows_section(
                "板块/概念暴露",
                report.get("sector_exposures"),
                (
                    ("sector_name", "板块/概念"),
                    ("sector_type", "类型"),
                    ("raw_weight", "原始权重"),
                    ("holding_count", "持仓数"),
                    ("names", "股票"),
                ),
            ),
            _html_rows_section(
                "持仓明细",
                report.get("holdings"),
                (
                    ("stock_code", "代码"),
                    ("stock_name", "名称"),
                    ("weight", "权重"),
                    ("industry", "行业"),
                    ("source", "来源"),
                ),
            ),
            _html_data_gaps_section(report.get("data_gaps")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _safe_fetch_profile(
    data_source: Any,
    config: FundHoldingExposureConfig,
    failures: list[dict[str, str]],
) -> list[dict[str, Any]]:
    try:
        return [
            dict(row)
            for row in data_source.fetch_fund_profile(fund_code=config.fund_code)
        ]
    except Exception as exc:
        failures.append({"capability": "fund_profile", "reason": str(exc)})
        return []


def _safe_fetch_holdings(
    data_source: Any,
    config: FundHoldingExposureConfig,
    failures: list[dict[str, str]],
) -> list[dict[str, Any]]:
    try:
        return [
            dict(row)
            for row in data_source.fetch_fund_holdings(
                fund_code=config.fund_code,
                limit=config.limit,
            )
        ]
    except Exception as exc:
        failures.append({"capability": "fund_holdings", "reason": str(exc)})
        return []


def _safe_fetch_memberships(
    data_source: Any,
    config: FundHoldingExposureConfig,
    holdings: list[dict[str, Any]],
    failures: list[dict[str, str]],
) -> list[dict[str, Any]]:
    symbols = _membership_symbols(holdings)
    if not symbols:
        return []
    try:
        return [
            dict(row)
            for row in data_source.fetch_stock_sector_memberships(
                symbols=symbols,
                trade_date=config.sector_trade_date,
                sector_types=list(config.sector_types),
                limit_per_symbol=config.limit_per_symbol,
                sector_universe_limit=config.sector_universe_limit,
            )
        ]
    except Exception as exc:
        failures.append({"capability": "stock_sector_membership", "reason": str(exc)})
        return []


def _fund_payload(fund_code: str, profile_rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile = profile_rows[0] if profile_rows else {}
    return {
        "fund_code": fund_code,
        "fund_name": str(profile.get("fund_name") or f"Fund {fund_code}"),
        "fund_type": str(profile.get("fund_type") or ""),
        "currency": str(profile.get("currency") or ""),
        "source": str(profile.get("source") or profile.get("provider") or ""),
    }


def _holding_payload(row: dict[str, Any]) -> dict[str, Any]:
    stock_code = _plain_stock_code(row.get("stock_code") or row.get("symbol") or "")
    ts_code = str(row.get("ts_code") or row.get("symbol") or _infer_ts_code(stock_code))
    return {
        "stock_code": stock_code,
        "ts_code": ts_code,
        "stock_name": str(row.get("stock_name") or row.get("name") or ""),
        "weight": _rounded(_float(row.get("weight"))),
        "industry": str(row.get("industry") or ""),
        "source": str(row.get("source") or row.get("provider") or ""),
        "as_of_date": str(row.get("as_of_date") or ""),
    }


def _industry_exposures(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for holding in holdings:
        industry = str(holding.get("industry") or "未分类")
        current = grouped.setdefault(
            industry,
            {
                "industry": industry,
                "raw_weight": 0.0,
                "holding_count": 0,
                "symbols": set(),
                "names": {},
            },
        )
        current["raw_weight"] += float(holding["weight"])
        current["holding_count"] += 1
        current["symbols"].add(str(holding["stock_code"]))
        current["names"][str(holding["stock_code"])] = str(holding["stock_name"])
    return _finalize_weight_groups(grouped.values(), name_field="industry")


def _sector_exposures(
    holdings: list[dict[str, Any]],
    membership_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    holdings_by_symbol = _holdings_by_membership_symbol(holdings)
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in membership_rows:
        symbol = str(row.get("symbol") or "")
        holding = holdings_by_symbol.get(symbol) or holdings_by_symbol.get(_plain_stock_code(symbol))
        sector_name = str(row.get("sector_name") or "")
        if holding is None or not sector_name:
            continue
        key = (sector_name, str(row.get("sector_type") or ""))
        current = grouped.setdefault(
            key,
            {
                "sector_name": sector_name,
                "sector_type": key[1],
                "raw_weight": 0.0,
                "holding_count": 0,
                "symbols": set(),
                "names": {},
                "source": str(row.get("source") or row.get("provider") or ""),
            },
        )
        current["raw_weight"] += float(holding["weight"])
        current["holding_count"] += 1
        current["symbols"].add(str(holding["stock_code"]))
        current["names"][str(holding["stock_code"])] = str(holding["stock_name"])
    return _finalize_weight_groups(grouped.values(), name_field="sector_name")


def _narrative_exposures(
    *,
    holdings: list[dict[str, Any]],
    narrative_registry: dict[str, Any],
    stock_narrative_mappings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    registry_by_id = _registry_by_id(narrative_registry)
    mappings_by_stock = _mappings_by_stock(stock_narrative_mappings)
    grouped: dict[str, dict[str, Any]] = {}
    for holding in holdings:
        stock_code = str(holding["stock_code"])
        for mapping in mappings_by_stock.get(stock_code, []):
            narrative_id = str(mapping.get("narrative_id") or "")
            if not narrative_id:
                continue
            mapping_weight = _float(mapping.get("mapping_weight"), default=1.0)
            confidence = _float(mapping.get("confidence"), default=0.0)
            contribution = float(holding["weight"]) * mapping_weight
            current = grouped.setdefault(
                narrative_id,
                {
                    "narrative_id": narrative_id,
                    "narrative_name": _narrative_name(registry_by_id, narrative_id),
                    "raw_exposure": 0.0,
                    "confidence_numerator": 0.0,
                    "holding_count": 0,
                    "symbols": set(),
                    "names": {},
                    "methods": set(),
                },
            )
            current["raw_exposure"] += contribution
            current["confidence_numerator"] += contribution * confidence
            current["holding_count"] += 1
            current["symbols"].add(stock_code)
            current["names"][stock_code] = str(holding["stock_name"])
            if mapping.get("method"):
                current["methods"].add(str(mapping["method"]))
    total = sum(float(item["raw_exposure"]) for item in grouped.values())
    rows = []
    for item in grouped.values():
        raw_exposure = float(item["raw_exposure"])
        symbols = sorted(item["symbols"])
        confidence = (
            _rounded(float(item["confidence_numerator"]) / raw_exposure)
            if raw_exposure > 0
            else 0.0
        )
        rows.append(
            {
                "narrative_id": item["narrative_id"],
                "narrative_name": item["narrative_name"],
                "raw_exposure": _rounded(raw_exposure),
                "normalized_exposure": _rounded(raw_exposure / total) if total else 0.0,
                "confidence": confidence,
                "holding_count": int(item["holding_count"]),
                "symbols": symbols,
                "names": [item["names"].get(symbol, "") for symbol in symbols],
                "methods": sorted(item["methods"]),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["raw_exposure"]), str(row["narrative_name"])))


def _intelligence_trust(
    *,
    narrative_registry: dict[str, Any],
    stock_narrative_mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    registry_trust = _mapping(narrative_registry.get("trust_metadata"))
    mapping_statuses = sorted(
        {
            str(mapping.get("source_trust_status") or "unspecified")
            for mapping in stock_narrative_mappings
        }
    )
    mapping_notes = sorted(
        {
            str(mapping.get("source_trust_note") or "")
            for mapping in stock_narrative_mappings
            if mapping.get("source_trust_note")
        }
    )
    registry_status = str(registry_trust.get("trust_status") or "unspecified")
    return {
        "registry_trust_status": registry_status,
        "registry_trust_status_label_zh": trust_state_display_zh(registry_status),
        "mapping_trust_statuses": mapping_statuses,
        "mapping_trust_status_labels_zh": [
            trust_state_display_zh(status) for status in mapping_statuses
        ],
        "trust_warning_zh": _trust_warning(registry_status, mapping_statuses),
        "registry_trust_note": str(registry_trust.get("trust_note") or ""),
        "mapping_trust_notes": mapping_notes,
    }


def _narrative_source_payload(value: dict[str, Any] | None) -> dict[str, Any]:
    source = _mapping(value)
    warnings = source.get("warnings") if isinstance(source.get("warnings"), list) else []
    diagnostics = _mapping(source.get("diagnostics"))
    return {
        "source": str(source.get("source") or "unspecified"),
        "provider": str(source.get("provider") or ""),
        "provider_version": str(source.get("provider_version") or ""),
        "data_fetch_mode": str(source.get("data_fetch_mode") or ""),
        "warning_count": len(warnings),
        "warnings": [dict(item) for item in warnings if isinstance(item, dict)],
        "diagnostics": dict(diagnostics),
    }


def _trust_warning(registry_status: str, mapping_statuses: list[str]) -> str:
    if registry_status == "trusted_validated" and mapping_statuses == ["trusted_validated"]:
        return "叙事定义和股票映射已标记为可信验证数据。"
    return (
        "当前叙事定义和股票映射仅为实验性本地知识种子，尚未证明来源链条、"
        "映射逻辑和复核标准足够严谨；相关暴露只能用于观察和审计。"
    )


def _data_gaps(
    *,
    profile_rows: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    membership_rows: list[dict[str, Any]],
    narrative_exposures: list[dict[str, Any]],
    stock_narrative_mappings: list[dict[str, Any]],
    failures: list[dict[str, str]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if not profile_rows:
        gaps.append(
            {
                "scope": "fund_profile",
                "requested": 1,
                "actual": 0,
                "missing": 1,
                "reason": "基金档案没有返回；报告使用 fund_code 兜底展示。",
            }
        )
    if not holdings:
        gaps.append(
            {
                "scope": "fund_holdings",
                "requested": 1,
                "actual": 0,
                "missing": 1,
                "reason": "基金持仓没有返回，无法计算暴露。",
            }
        )
        return gaps
    if any(item["capability"] == "stock_sector_membership" for item in failures):
        gaps.append(
            {
                "scope": "sector_membership_unavailable",
                "requested": len(holdings),
                "actual": 0,
                "missing": len(holdings),
                "reason": "股票到板块/概念反查失败；行业和叙事暴露仍可继续计算。",
            }
        )
    else:
        missing_membership = _missing_membership_symbols(holdings, membership_rows)
        if missing_membership:
            gaps.append(
                {
                    "scope": "stock_sector_membership_symbols",
                    "requested": len(holdings),
                    "actual": len(holdings) - len(missing_membership),
                    "missing": len(missing_membership),
                    "reason": "部分基金持仓没有返回板块/概念归属。",
                    "missing_symbols": missing_membership,
                }
            )
    unmapped = _unmapped_symbols(holdings, stock_narrative_mappings, narrative_exposures)
    if unmapped:
        gaps.append(
            {
                "scope": "unmapped_fund_holding_symbols",
                "requested": len(holdings),
                "actual": len(holdings) - len(unmapped),
                "missing": len(unmapped),
                "reason": "部分基金持仓没有本地叙事映射，暂不计入叙事暴露。",
                "missing_symbols": unmapped,
            }
        )
    return gaps


def _status(
    *,
    holdings: list[dict[str, Any]],
    failures: list[dict[str, str]],
    data_gaps: list[dict[str, Any]],
) -> str:
    if holdings and not failures and not data_gaps:
        return "completed"
    if holdings:
        return "partial"
    if failures:
        return "failed"
    return "missing"


def _finalize_weight_groups(
    groups: Any,
    *,
    name_field: str,
) -> list[dict[str, Any]]:
    rows = list(groups)
    total = sum(float(row["raw_weight"]) for row in rows)
    output = []
    for row in rows:
        symbols = sorted(row["symbols"])
        output.append(
            {
                name_field: row[name_field],
                **({"sector_type": row["sector_type"]} if "sector_type" in row else {}),
                "raw_weight": _rounded(float(row["raw_weight"])),
                "normalized_weight": _rounded(float(row["raw_weight"]) / total)
                if total
                else 0.0,
                "holding_count": int(row["holding_count"]),
                "symbols": symbols,
                "names": [row["names"].get(symbol, "") for symbol in symbols],
                **({"source": row["source"]} if row.get("source") else {}),
            }
        )
    return sorted(output, key=lambda item: (-float(item["raw_weight"]), str(item[name_field])))


def _membership_symbols(holdings: list[dict[str, Any]]) -> list[str]:
    seen = set()
    symbols = []
    for holding in holdings:
        symbol = str(holding.get("ts_code") or _infer_ts_code(holding.get("stock_code")))
        if symbol and symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)
    return symbols


def _holdings_by_membership_symbol(holdings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for holding in holdings:
        stock_code = str(holding["stock_code"])
        ts_code = str(holding.get("ts_code") or _infer_ts_code(stock_code))
        result[stock_code] = holding
        result[ts_code] = holding
    return result


def _missing_membership_symbols(
    holdings: list[dict[str, Any]],
    membership_rows: list[dict[str, Any]],
) -> list[str]:
    covered = {_plain_stock_code(row.get("symbol") or "") for row in membership_rows}
    return [
        str(holding["stock_code"])
        for holding in holdings
        if str(holding["stock_code"]) not in covered
    ]


def _unmapped_symbols(
    holdings: list[dict[str, Any]],
    stock_narrative_mappings: list[dict[str, Any]],
    narrative_exposures: list[dict[str, Any]],
) -> list[str]:
    del narrative_exposures
    mapped = {
        _plain_stock_code(mapping.get("stock_code") or mapping.get("symbol") or "")
        for mapping in stock_narrative_mappings
        if mapping.get("narrative_id")
    }
    return [
        str(holding["stock_code"])
        for holding in holdings
        if str(holding["stock_code"]) not in mapped
    ]


def _mappings_by_stock(
    stock_narrative_mappings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for mapping in stock_narrative_mappings:
        stock_code = _plain_stock_code(mapping.get("stock_code") or mapping.get("symbol") or "")
        if stock_code:
            grouped[stock_code].append(mapping)
    return grouped


def _registry_by_id(narrative_registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    narratives = narrative_registry.get("narratives") if isinstance(narrative_registry, dict) else []
    if not isinstance(narratives, list):
        return {}
    return {
        str(item.get("narrative_id")): item
        for item in narratives
        if isinstance(item, dict) and item.get("narrative_id")
    }


def _narrative_name(registry_by_id: dict[str, dict[str, Any]], narrative_id: str) -> str:
    narrative = registry_by_id.get(narrative_id, {})
    return str(
        narrative.get("display_name")
        or narrative.get("canonical_name_zh")
        or narrative.get("name")
        or narrative_id
    )


def _plain_stock_code(value: Any) -> str:
    text = str(value or "").strip()
    if "." in text:
        return text.split(".", 1)[0]
    return text


def _infer_ts_code(value: Any) -> str:
    stock_code = _plain_stock_code(value)
    if not stock_code:
        return ""
    suffix = "SH" if stock_code.startswith("6") else "SZ"
    return f"{stock_code}.{suffix}"


def _float(value: Any, *, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_text(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _html_rows_section(
    title: str,
    value: Any,
    columns: tuple[tuple[str, str], ...],
) -> str:
    rows = value if isinstance(value, list) else []
    return "\n".join(
        [
            "<section>",
            f"<h2>{_html_text(title)}</h2>",
            _rows_table(rows, columns),
            "</section>",
        ]
    )


def _html_data_gaps_section(value: Any) -> str:
    gaps = value if isinstance(value, list) else []
    if not gaps:
        return "<section><h2>数据缺口</h2><p>无。</p></section>"
    return _html_rows_section(
        "数据缺口",
        gaps,
        (
            ("scope", "范围"),
            ("requested", "请求"),
            ("actual", "实际"),
            ("missing", "缺失"),
            ("reason", "说明"),
        ),
    )


def _rows_table(rows: list[dict[str, Any]], columns: tuple[tuple[str, str], ...]) -> str:
    if not rows:
        return '<p class="empty">没有返回可展示数据。</p>'
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{_html_text(_cell_value(row.get(field)))}</td>"
            for field, _ in columns
        )
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _cell_value(value: Any) -> Any:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return value


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _html_trust_notice(value: Any) -> str:
    trust = _mapping(value)
    warning = trust.get("trust_warning_zh")
    if not warning:
        return ""
    mapping_labels = _list_text(trust.get("mapping_trust_status_labels_zh"))
    rows = [
        f'<p class="trust-warning">{_html_text(warning)}</p>',
        _html_kv("注册表信任状态", trust.get("registry_trust_status_label_zh", "")),
    ]
    if mapping_labels:
        rows.append(_html_kv("映射信任状态", ", ".join(mapping_labels)))
    return "\n".join(rows)


def _html_narrative_source_notice(value: Any) -> str:
    return _html_source_notice("叙事数据来源", value)


def _html_market_data_source_notice(value: Any) -> str:
    return _html_source_notice("市场数据来源", value)


def _html_source_notice(title: str, value: Any) -> str:
    source = _mapping(value)
    return "\n".join(
        [
            '<div class="source-notice">',
            f"<h2>{_html_text(title)}</h2>",
            _html_kv("来源", source.get("source", "unspecified")),
            _html_kv("Provider", source.get("provider", "")),
            _html_kv("模式", source.get("data_fetch_mode", "")),
            _html_kv("告警数", source.get("warning_count", 0)),
            _html_kv("降级状态", source_status_zh(source)),
            _html_kv("回退来源", source_fallback_zh(source)),
            _html_kv("告警说明", source_warning_summary_zh(source)),
            "</div>",
        ]
    )


def _status_label(status: str) -> str:
    return {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "missing": "无数据",
    }.get(status, status)


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #2563eb; }
.trust-warning { border: 1px solid #f59e0b; background: #fffbeb; color: #92400e; padding: 10px; }
.source-notice { border: 1px solid #cbd5e1; background: #f8fafc; padding: 10px; margin: 10px 0; }
.source-notice h2 { font-size: 16px; margin: 0 0 8px; }
.source-notice p { margin: 4px 0; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.metric { border: 1px solid #e3e8ef; padding: 10px; background: #fbfcfe; }
.metric span { display: block; color: #5b6472; font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 18px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #e6ebf1; padding: 8px; text-align: left; vertical-align: top; }
th { color: #475569; background: #f8fafc; }
.empty { color: #8a94a6; }
""".strip()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
