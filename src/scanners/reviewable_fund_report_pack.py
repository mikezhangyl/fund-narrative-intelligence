from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from src.validation import (
    validate_pipeline_artifact_manifest_payload,
    validate_review_queue_artifact_payload,
)


def build_reviewable_fund_report_pack(
    *,
    artifact_root: Path,
    reference_artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    manifest_path = _resolve_manifest_path(artifact_root)
    root = manifest_path.parent
    manifest = _read_json(manifest_path)
    validate_pipeline_artifact_manifest_payload(manifest)
    raw = _read_artifact(root, manifest, "raw")
    scoring = _read_artifact(root, manifest, "scoring")
    review_queue = _read_artifact(root, manifest, "review_queue")
    validate_review_queue_artifact_payload(review_queue)
    holdings = _list(raw.get("holdings"))
    narratives = _narrative_rows(scoring)
    review_workspace = _review_workspace(review_queue)
    return {
        "version": "reviewable-fund-report-pack-v1",
        "generated_at": _utc_now(),
        "status": "review_ready",
        "fund": _mapping(raw.get("fund")),
        "manifest": {
            "path": manifest_path.name,
            "run_id": manifest["run_id"],
            "generated_at": manifest["generated_at"],
            "fund_code": manifest["fund_code"],
            "source_modes": manifest["source_modes"],
            "warning_counts": manifest["warning_counts"],
        },
        "summary": {
            "holding_count": len(holdings),
            "narrative_count": len(narratives),
            "artifact_count": len(manifest["artifacts"]),
            "reference_artifact_count": len(reference_artifacts or {}),
            "review_item_count": review_workspace["review_item_count"],
            "data_gap_count": _data_gap_count(manifest),
        },
        "source_modes": manifest["source_modes"],
        "trust_disclosure": manifest["trust_states"],
        "data_gap_summary": manifest["warning_counts"],
        "artifact_links": _artifact_links(manifest),
        "reference_artifacts": _reference_artifacts(reference_artifacts),
        "holdings": _holding_rows(holdings),
        "narrative_exposures": narratives,
        "review_workspace": review_workspace,
        "disclaimer": (
            "Reviewable fund report pack is for audit and review workflow only; "
            "it is not investment advice, portfolio recommendation, trading "
            "strategy, or prediction."
        ),
    }


def render_html_report(pack: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>基金审查报告包</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>基金审查报告包</h1>",
            '<section class="summary">',
            _html_kv("状态", pack.get("status", "")),
            _html_kv("生成时间", pack.get("generated_at", "")),
            _html_kv("基金", _fund_label(pack.get("fund"))),
            _html_kv("候选状态", _mapping(pack.get("trust_disclosure")).get("candidate_outputs", "")),
            "<p>本报告包用于集中审查持仓、叙事暴露、来源、数据缺口和 Review Queue，不构成投资建议、组合推荐、交易策略或预测。</p>",
            "</section>",
            _rows_section(
                "核心 Artifact",
                pack.get("artifact_links"),
                (
                    ("artifact_key", "Artifact"),
                    ("path", "路径"),
                    ("format", "格式"),
                    ("source_control", "入库策略"),
                ),
                link_field="path",
            ),
            _rows_section(
                "参考报告",
                pack.get("reference_artifacts"),
                (("artifact_key", "报告"), ("path", "路径")),
                link_field="path",
            ),
            _rows_section(
                "持仓概览",
                pack.get("holdings"),
                (("stock_code", "股票"), ("stock_name", "名称"), ("weight", "权重")),
            ),
            _rows_section(
                "叙事暴露",
                pack.get("narrative_exposures"),
                (
                    ("narrative_name", "叙事"),
                    ("raw_exposure", "原始暴露"),
                    ("weighted_score", "加权分"),
                    ("trust_status", "状态"),
                ),
            ),
            _source_gap_section(pack),
            _review_workspace_section(pack.get("review_workspace")),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _resolve_manifest_path(path: Path) -> Path:
    if path.is_file():
        return path
    manifests = sorted(path.glob("fund_*_manifest.json"))
    if len(manifests) != 1:
        raise ValueError(f"{path} must contain exactly one fund manifest")
    return manifests[0]


def _read_artifact(root: Path, manifest: dict[str, Any], key: str) -> dict[str, Any]:
    descriptor = _mapping(manifest["artifacts"].get(key))
    path = root / str(descriptor.get("path") or "")
    return _read_json(path)


def _artifact_links(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "artifact_key": key,
            "path": str(descriptor.get("path") or ""),
            "format": str(descriptor.get("format") or ""),
            "source_control": str(descriptor.get("source_control") or ""),
            "reader_surface": bool(descriptor.get("reader_surface")),
        }
        for key, descriptor in sorted(manifest["artifacts"].items())
        if isinstance(descriptor, dict)
    ]


def _reference_artifacts(value: dict[str, str] | None) -> list[dict[str, str]]:
    return [
        {"artifact_key": key, "path": path}
        for key, path in sorted((value or {}).items())
    ]


def _holding_rows(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "stock_code": str(item.get("stock_code") or ""),
            "stock_name": str(item.get("stock_name") or ""),
            "weight": _rounded(_float(item.get("weight"))),
        }
        for item in holdings
    ]


def _narrative_rows(scoring: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    candidates = [
        _mapping(scoring.get("primary_narrative")),
        *_list(scoring.get("secondary_narratives")),
    ]
    for item in candidates:
        narrative_id = str(item.get("narrative_id") or "")
        if not narrative_id:
            continue
        rows.append(
            {
                "narrative_id": narrative_id,
                "narrative_name": str(item.get("narrative_name") or item.get("display_name") or narrative_id),
                "raw_exposure": _rounded(_float(item.get("raw_exposure"))),
                "weighted_score": _rounded(_float(item.get("weighted_score"))),
                "trust_status": str(item.get("trust_status") or "candidate_untrusted"),
            }
        )
    return rows


def _review_workspace(review_queue: dict[str, Any]) -> dict[str, Any]:
    queue = _mapping(review_queue.get("candidate_review_queue"))
    items = _list(queue.get("items"))
    return {
        "version": "review-workspace-links-v1",
        "review_item_count": len(items),
        "pending_review_item_count": sum(
            1 for item in items if str(item.get("status") or "pending") == "pending"
        ),
        "items": [
            {
                "review_item_id": str(item.get("review_item_id") or item.get("id") or ""),
                "title": str(item.get("title") or ""),
                "status": str(item.get("status") or "pending"),
                "trust_status": str(item.get("trust_status") or "candidate_untrusted"),
            }
            for item in items
        ],
    }


def _data_gap_count(manifest: dict[str, Any]) -> int:
    counts = _mapping(manifest.get("warning_counts"))
    return int(counts.get("total_warning_count") or 0)


def _source_gap_section(pack: dict[str, Any]) -> str:
    source_modes = _mapping(pack.get("source_modes"))
    layers = _mapping(source_modes.get("layers"))
    rows = [
        {
            "layer": layer,
            "provider_name": item.get("provider_name"),
            "data_quality": item.get("data_quality"),
            "is_mock": item.get("is_mock"),
        }
        for layer, item in sorted(layers.items())
        if isinstance(item, dict)
    ]
    gaps = _mapping(pack.get("data_gap_summary"))
    return "\n".join(
        [
            "<section><h2>来源与数据缺口</h2>",
            _rows_table(
                rows,
                (
                    ("layer", "数据层"),
                    ("provider_name", "Provider"),
                    ("data_quality", "质量"),
                    ("is_mock", "Mock"),
                ),
            ),
            f"<p>warning_count: {_html_text(gaps.get('total_warning_count', 0))}</p>",
            "</section>",
        ]
    )


def _review_workspace_section(value: Any) -> str:
    workspace = _mapping(value)
    return "\n".join(
        [
            "<section><h2>Review Queue</h2>",
            _html_kv("待审项", workspace.get("pending_review_item_count", 0)),
            _rows_table(
                _list(workspace.get("items")),
                (
                    ("review_item_id", "ID"),
                    ("title", "标题"),
                    ("status", "状态"),
                    ("trust_status", "信任状态"),
                ),
            ),
            "</section>",
        ]
    )


def _rows_section(
    title: str,
    rows: Any,
    columns: tuple[tuple[str, str], ...],
    *,
    link_field: str | None = None,
) -> str:
    return (
        f"<section><h2>{_html_text(title)}</h2>"
        f"{_rows_table(_list(rows), columns, link_field=link_field)}"
        "</section>"
    )


def _rows_table(
    rows: list[dict[str, Any]],
    columns: tuple[tuple[str, str], ...],
    *,
    link_field: str | None = None,
) -> str:
    if not rows:
        return '<p class="empty">没有返回可展示数据。</p>'
    header = "".join(f"<th>{_html_text(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = _cell(row.get(key))
            if link_field == key and value:
                cells.append(f'<td><a href="{_html_text(value)}">{_html_text(value)}</a></td>')
            else:
                cells.append(f"<td>{_html_text(value)}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _fund_label(value: Any) -> str:
    fund = _mapping(value)
    return f"{fund.get('fund_name', '')} ({fund.get('fund_code', '')})"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _cell(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 18px; margin: 16px 0; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 0 0 12px; }
p { line-height: 1.65; }
.summary { border-left: 4px solid #16a34a; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #e5e7eb; padding: 8px 10px; text-align: left; }
th { background: #f3f4f6; }
a { color: #1d4ed8; }
.empty { color: #8a94a6; }
""".strip()
