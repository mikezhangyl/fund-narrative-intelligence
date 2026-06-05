from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from html import escape
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data.capabilities import (  # noqa: E402
    DEFAULT_CAPABILITY_CONFIG_PATH,
    DataCapabilityRegistry,
    load_data_capability_registry,
)

OutputFormat = Literal["markdown", "json", "html"]

STATUS_LABELS = {
    "can_do": "Can-Do: runnable today with explicit source diagnostics.",
    "unstable": "Unstable: reachable but not reliable enough for stable use.",
    "blocked": "Blocked: missing, disabled, or unavailable for current reports.",
    "future": "Future: planned capability that should not drive current reports.",
}

CAPABILITY_GROUPS = (
    {
        "group_id": "daily_bars",
        "name": "Daily Bars / Market Context",
        "dataset_ids": (
            "a_share_daily_bars",
            "index_bars",
            "etf_daily",
            "latest_stock_quotes",
            "etf_spot_ranking",
            "stock_metadata",
            "trade_calendar",
            "turnover_rate",
        ),
    },
    {
        "group_id": "fund_holdings",
        "name": "Fund Holdings",
        "dataset_ids": ("fund_profile", "fund_holdings"),
    },
    {
        "group_id": "sectors",
        "name": "Sectors",
        "dataset_ids": (
            "sector_concepts",
            "sector_constituents",
            "stock_sector_membership",
        ),
    },
    {
        "group_id": "flows",
        "name": "Flows / Events",
        "dataset_ids": (
            "northbound_capital",
            "main_capital_flow",
            "etf_flow",
            "dragon_tiger_list",
            "limit_up_down_stats",
        ),
    },
    {
        "group_id": "structure_mapping",
        "name": "Structure Mapping",
        "dataset_ids": (
            "etf_basic",
            "index_constituents",
            "margin_summary",
            "margin_detail",
            "earnings_calendar",
        ),
    },
    {
        "group_id": "news",
        "name": "News",
        "dataset_ids": (
            "news_briefs",
            "narrative_source_events",
            "narrative_source_events_legacy_fixture",
        ),
    },
    {"group_id": "cyq", "name": "CYQ / Cost Basis", "dataset_ids": ("cyq_chips",)},
    {
        "group_id": "narrative_service",
        "name": "Narrative Service",
        "dataset_ids": (
            "narrative_service",
            "narrative_official_filings",
            "narrative_official_disclosures",
            "narrative_news_context",
            "narrative_social_heat",
        ),
    },
)

GROUP_BY_DATASET_ID = {
    dataset_id: str(group["group_id"])
    for group in CAPABILITY_GROUPS
    for dataset_id in group["dataset_ids"]
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the market-data capability registry."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CAPABILITY_CONFIG_PATH,
        help="Path to data_capabilities.yaml.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "html"),
        default="markdown",
        dest="output_format",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    registry = load_data_capability_registry(args.config)
    report = build_report(registry, output_format=args.output_format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


def build_report(
    registry: DataCapabilityRegistry,
    *,
    output_format: OutputFormat,
) -> str:
    inventory = build_inventory_report(registry)
    if output_format == "json":
        return json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True)
    if output_format == "html":
        return _html_report(inventory)
    if output_format != "markdown":
        raise ValueError(f"unsupported data capability report format: {output_format}")
    return _markdown_report(inventory)


def build_inventory_report(registry: DataCapabilityRegistry) -> dict[str, object]:
    dataset_rows = [
        _dataset_row(dataset_id=dataset_id, dataset=dataset)
        for dataset_id, dataset in registry.datasets.items()
    ]
    dataset_rows.append(_narrative_service_row())
    groups = []
    for group in CAPABILITY_GROUPS:
        rows = [
            row for row in dataset_rows if row["group_id"] == group["group_id"]
        ]
        groups.append(
            {
                "group_id": group["group_id"],
                "name": group["name"],
                "dataset_count": len(rows),
                "status_label_counts": dict(
                    sorted(Counter(row["trust_stability_label"] for row in rows).items())
                ),
                "dataset_ids": [row["dataset_id"] for row in rows],
            }
        )
    inventory = registry.to_dict()
    inventory.update(
        {
            "inventory_version": "data-capability-inventory-v1",
            "status_labels": dict(STATUS_LABELS),
            "inventory_summary": {
                "dataset_row_count": len(dataset_rows),
                "status_label_counts": dict(
                    sorted(
                        Counter(
                            row["trust_stability_label"] for row in dataset_rows
                        ).items()
                    )
                ),
                "group_count": len(groups),
            },
            "inventory_groups": groups,
            "dataset_rows": dataset_rows,
        }
    )
    return inventory


def _markdown_report(inventory: dict[str, object]) -> str:
    summary = _mapping(inventory.get("summary"))
    lines = [
        "# Data Capability Registry",
        "",
        f"- Version: `{inventory.get('version', '')}`",
        f"- Updated at: `{inventory.get('updated_at', '')}`",
        f"- Dataset count: `{summary['dataset_count']}`",
        f"- Analysis capability count: `{summary['analysis_capability_count']}`",
        "",
        "## Gateway Ownership Boundary",
        "",
        *_ownership_policy_lines(_mapping(inventory.get("ownership_policy"))),
        "",
        "## Status Labels",
        "",
        *_status_label_lines(_mapping(inventory.get("status_labels"))),
        "",
        "## Dataset Status",
        "",
    ]
    lines.extend(_counts_markdown(_int_mapping(summary.get("dataset_status_counts"))))
    lines.extend(["", "## Gateway Mode", ""])
    lines.extend(_counts_markdown(_int_mapping(summary.get("gateway_mode_counts"))))
    lines.extend(
        [
            "",
            "## Datasets",
            "",
            "| Dataset | Group | Status | Label | Gateway | Primary Source | Last Smoke | Degradation Behavior |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in _list_of_mappings(inventory.get("dataset_rows")):
        lines.append(
            "| {dataset_id} | {group} | {status} | {label} | {gateway} | {source} | {smoke} | {degradation} |".format(
                dataset_id=row.get("dataset_id", ""),
                group=row.get("group_id", ""),
                status=row.get("fni_consumer_status", ""),
                label=row.get("trust_stability_label", ""),
                gateway=row.get("gateway_mode", ""),
                source=f"{row.get('source_provider', '')}.{row.get('source_endpoint', '')}",
                smoke=row.get("last_smoke_status", ""),
                degradation=row.get("degradation_behavior", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Analysis Capabilities",
            "",
            "| Capability | Status | Complexity | Can Run | Blockers | Warnings | Required Datasets | Metrics |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    analysis = _mapping(inventory.get("analysis_capabilities"))
    readiness_by_id = _mapping(inventory.get("analysis_readiness"))
    for capability_id, capability_value in analysis.items():
        capability = _mapping(capability_value)
        readiness = _mapping(readiness_by_id.get(capability_id))
        lines.append(
            "| {capability_id} | {status} | {complexity} | {can_run} | {blockers} | {warnings} | {datasets} | {metrics} |".format(
                capability_id=capability_id,
                status=capability.get("implementation_status", ""),
                complexity=capability.get("complexity", ""),
                can_run=readiness.get("can_run", ""),
                blockers=", ".join(_string_list(readiness.get("blockers"))),
                warnings=", ".join(_string_list(readiness.get("warnings"))),
                datasets=", ".join(_string_list(capability.get("required_datasets"))),
                metrics=", ".join(_string_list(capability.get("output_metrics"))),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _dataset_row(*, dataset_id: str, dataset: object) -> dict[str, object]:
    primary_source = dataset.primary_source
    return {
        "dataset_id": dataset_id,
        "group_id": GROUP_BY_DATASET_ID.get(dataset_id, "other"),
        "description": dataset.description,
        "fni_consumer_status": dataset.current_status,
        "trust_stability_label": _status_label(dataset.current_status),
        "acquisition_difficulty": dataset.acquisition_difficulty,
        "gateway_mode": dataset.gateway_mode,
        "source_provider": primary_source.provider,
        "source_endpoint": primary_source.endpoint,
        "source_access_mode": primary_source.access_mode,
        "fallback_source_count": len(dataset.fallback_sources),
        "last_smoke_status": _last_smoke_status(dataset),
        "degradation_behavior": _degradation_behavior(dataset),
        "required_fields": list(dataset.required_fields),
        "analysis_use_cases": list(dataset.analysis_use_cases),
        "notes": list(dataset.notes),
    }


def _narrative_service_row() -> dict[str, object]:
    return {
        "dataset_id": "narrative_service",
        "group_id": "narrative_service",
        "description": (
            "Narrative Service HTTP contract and local prototype fallback for "
            "registry, mappings, candidates, evidence packs, review queue, and "
            "promotion preflight."
        ),
        "fni_consumer_status": "available",
        "trust_stability_label": "can_do",
        "acquisition_difficulty": "medium",
        "gateway_mode": "service_contract",
        "source_provider": "narrative-service",
        "source_endpoint": "/api/v1/narratives/...",
        "source_access_mode": "http_service_with_local_fallback",
        "fallback_source_count": 1,
        "last_smoke_status": "validate_stock_narrative_service_acceptance: can_do",
        "degradation_behavior": (
            "When the service is unavailable, FNI falls back to the local "
            "prototype provider with explicit warnings and narrative_source "
            "diagnostics."
        ),
        "required_fields": [
            "status",
            "source",
            "provider",
            "provider_version",
            "data",
            "warnings",
            "trust_metadata",
        ],
        "analysis_use_cases": [
            "fund_holding_exposure_report",
            "fund_exposure_comparison_report",
            "fund_narrative_exposure_matrix_report",
            "candidate_narrative_intake",
        ],
        "notes": [
            (
                "Narrative Service is not market data, but report source "
                "reliability depends on it."
            ),
        ],
    }


def _status_label(status: str) -> str:
    if status == "available":
        return "can_do"
    if status == "unstable":
        return "unstable"
    if status in {"missing", "disabled"}:
        return "blocked"
    if status == "planned":
        return "future"
    return "blocked"


def _last_smoke_status(dataset: object) -> str:
    probe = dataset.validation_probe_capability or "no_probe"
    status = dataset.current_status
    if status == "available":
        return f"{probe}: can_do"
    if status == "unstable":
        return f"{probe}: degraded_or_unstable"
    if status == "planned":
        return f"{probe}: future"
    return f"{probe}: blocked"


def _degradation_behavior(dataset: object) -> str:
    notes = " ".join(dataset.notes)
    if dataset.current_status == "unstable":
        return (
            "May return structured degraded or missing payloads; keep visible in "
            "failures/degradation_events and do not treat as stable."
        )
    if dataset.fallback_sources:
        return (
            "Fallback or compatibility sources are explicit; provider failures "
            "should surface as degradation_events or data gaps."
        )
    if "degraded" in notes.lower():
        return notes
    return "No special fallback; request failures should be reported as data gaps."


def _counts_markdown(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- None"]
    return [f"- `{key}`: `{value}`" for key, value in sorted(counts.items())]


def _ownership_policy_lines(policy: dict[str, object]) -> list[str]:
    if not policy:
        return ["- Not declared"]
    return [
        f"- External source expansion owner: `{policy.get('external_source_expansion_owner', '')}`",
        f"- FNI role: `{policy.get('fni_role', '')}`",
        f"- Direct external source rule: `{policy.get('direct_external_source_rule', '')}`",
        f"- Change request location: `{policy.get('change_request_location', '')}`",
        f"- Report disclosure required: `{policy.get('report_disclosure_required', '')}`",
    ]


def _status_label_lines(labels: dict[str, object]) -> list[str]:
    if not labels:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in labels.items()]


def _html_report(inventory: dict[str, object]) -> str:
    summary = _mapping(inventory.get("summary"))
    rows = _list_of_mappings(inventory.get("dataset_rows"))
    groups = _list_of_mappings(inventory.get("inventory_groups"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>数据能力清单</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            "<h1>数据能力清单</h1>",
            "<section>",
            "<h2>总览</h2>",
            '<div class="metrics">',
            _html_metric(
                "数据集",
                summary.get("dataset_count", 0),
                "config/data_capabilities.yaml 中的数据集数量。",
            ),
            _html_metric(
                "分析能力",
                summary.get("analysis_capability_count", 0),
                "依赖数据集的分析/报告能力数量。",
            ),
            _html_metric("分组", len(groups), "PM 视角的数据能力分组数量。"),
            "</div>",
            "</section>",
            "<section>",
            "<h2>状态口径</h2>",
            _html_status_labels(_mapping(inventory.get("status_labels"))),
            "</section>",
            "<section>",
            "<h2>Gateway 边界</h2>",
            _html_policy(_mapping(inventory.get("ownership_policy"))),
            "</section>",
            *_html_group_sections(groups, rows),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _html_group_sections(
    groups: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> list[str]:
    sections: list[str] = []
    for group in groups:
        group_rows = [row for row in rows if row.get("group_id") == group.get("group_id")]
        sections.extend(
            [
                "<section>",
                f"<h2>{_html_text(group.get('name'))} <code>{_html_text(group.get('group_id'))}</code></h2>",
                _html_dataset_table(group_rows),
                "</section>",
            ]
        )
    return sections


def _html_dataset_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "<p>暂无数据。</p>"
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("数据集", "状态", "来源", "Smoke", "降级行为")
    )
    body_rows = []
    for row in rows:
        source = f"{row.get('source_provider', '')}.{row.get('source_endpoint', '')}"
        body_rows.append(
            "<tr>"
            f"<td><code>{_html_text(row.get('dataset_id'))}</code></td>"
            f"<td><span class=\"badge {_html_text(row.get('trust_stability_label'))}\">{_html_text(row.get('trust_stability_label'))}</span><br />{_html_text(row.get('fni_consumer_status'))}</td>"
            f"<td>{_html_text(source)}<br /><small>{_html_text(row.get('gateway_mode'))}</small></td>"
            f"<td>{_html_text(row.get('last_smoke_status'))}</td>"
            f"<td>{_html_text(row.get('degradation_behavior'))}</td>"
            "</tr>"
        )
    return (
        f"<table><thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def _html_metric(label: str, value: object, title: str) -> str:
    return (
        f'<div class="metric" title="{_html_text(title)}">'
        f"<span>{_html_text(label)}</span>"
        f"<strong>{_html_text(value)}</strong>"
        "</div>"
    )


def _html_status_labels(labels: dict[str, object]) -> str:
    items = "".join(
        f"<li><code>{_html_text(key)}</code>: {_html_text(value)}</li>"
        for key, value in labels.items()
    )
    return f"<ul>{items}</ul>"


def _html_policy(policy: dict[str, object]) -> str:
    items = "".join(
        f"<li><strong>{_html_text(key)}</strong>: {_html_text(value)}</li>"
        for key, value in policy.items()
        if key != "can_do_stability_labels"
    )
    return f"<ul>{items}</ul>"


def _html_styles() -> str:
    return """
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #18212f; background: #f7f9fb; }
main { max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }
h1 { font-size: 30px; margin: 0 0 22px; }
h2 { font-size: 20px; margin: 0 0 14px; }
section { margin: 0 0 24px; }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
.metric { border: 1px solid #d7dee8; background: #fff; padding: 12px; border-radius: 6px; }
.metric span { display: block; color: #5a6778; font-size: 13px; }
.metric strong { display: block; margin-top: 6px; font-size: 22px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d7dee8; }
th, td { padding: 10px; border-bottom: 1px solid #e7ebf0; text-align: left; vertical-align: top; font-size: 13px; }
th { background: #eef3f7; color: #344255; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
small { color: #5f6c7b; }
.badge { display: inline-block; border-radius: 999px; padding: 2px 8px; font-size: 12px; font-weight: 700; }
.can_do { background: #d9f4e5; color: #17633a; }
.unstable { background: #fff1c2; color: #765a00; }
.blocked { background: #ffe0df; color: #8a1f17; }
.future { background: #e7eaf1; color: #3f4b5f; }
""".strip()


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _int_mapping(value: object) -> dict[str, int]:
    mapping = _mapping(value)
    return {str(key): int(item) for key, item in mapping.items() if isinstance(item, int)}


def _list_of_mappings(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _html_text(value: object) -> str:
    return escape(str(value or ""), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
