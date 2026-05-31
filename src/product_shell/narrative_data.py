from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

SOURCE_PATHS = {
    "narrative_registry": "data/registry/narrative_registry.reviewed.json",
    "stock_mappings": "data/registry/stock_narrative_mappings.reviewed.json",
    "evidence_packs": "data/registry/mapping_evidence_packs.v0.json",
    "quality_audit": "outputs/narrative_quality/round5_final/narrative_quality_audit.json",
    "service_conformance": (
        "outputs/stock_narrative_service_acceptance/round5-final/conformance/"
        "narrative_service_conformance_report.json"
    ),
    "provider_smoke": (
        "outputs/stock_narrative_service_acceptance/round5-final/provider_smoke/"
        "narrative_service_provider_smoke.json"
    ),
}

SENSITIVE_KEY_PARTS = ("secret", "token", "password", "credential", "api_key")


def build_narrative_data_snapshot(
    *,
    project_root: Path,
    output_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    sources = {
        source_id: _load_source(project_root=project_root, relative_path=relative_path)
        for source_id, relative_path in SOURCE_PATHS.items()
    }
    registry = _mapping(sources["narrative_registry"].get("payload"))
    mappings = _mapping(sources["stock_mappings"].get("payload"))
    evidence_packs = _mapping(sources["evidence_packs"].get("payload"))
    quality_audit = _mapping(sources["quality_audit"].get("payload"))
    conformance = _mapping(sources["service_conformance"].get("payload"))
    provider_smoke = _mapping(sources["provider_smoke"].get("payload"))

    narratives = _sanitize(_list(registry.get("narratives")))
    candidate_narratives = _sanitize(_list(registry.get("candidate_narratives")))
    stock_mappings = _sanitize(_list(mappings.get("mappings")))
    pack_rows = _sanitize(_list(evidence_packs.get("packs")))
    scorecards = _sanitize(
        _list(quality_audit.get("evidence_pack_scorecards")) or _list(quality_audit.get("scorecards"))
    )
    issues = _sanitize(_list(quality_audit.get("issues")))
    extraction_issues = _sanitize(_list(quality_audit.get("extraction_confidence_issues")))
    source_artifacts = [_source_metadata(source) for source in sources.values()]
    available_count = sum(1 for source in source_artifacts if source["status"] == "available")

    consumer_policy = _mapping(quality_audit.get("consumer_policy")) or {
        "quality_authority": "narrative_service",
        "fni_recomputes_quality": False,
    }

    return {
        "version": "product-shell-narrative-data-v1",
        "generated_at": generated_at or _utc_now(),
        "source_scope": {
            "project_root": str(project_root),
            "output_root": str(output_root),
            "mode": "existing_artifacts_only",
        },
        "summary": {
            "narrative_count": len(narratives),
            "candidate_narrative_count": len(candidate_narratives),
            "stock_mapping_count": len(stock_mappings),
            "evidence_pack_count": len(pack_rows),
            "quality_scorecard_count": len(scorecards),
            "quality_issue_count": len(issues),
            "extraction_issue_count": len(extraction_issues),
            "available_source_count": available_count,
            "missing_source_count": len(source_artifacts) - available_count,
        },
        "consumer_policy": _sanitize(consumer_policy),
        "source_artifacts": source_artifacts,
        "narratives": narratives,
        "candidate_narratives": candidate_narratives,
        "stock_mappings": stock_mappings,
        "evidence_packs": pack_rows,
        "evidence_pack_scorecards": scorecards,
        "quality_issues": issues,
        "extraction_confidence_issues": extraction_issues,
        "service_health": {
            "conformance": _sanitize(_mapping(conformance.get("result"))),
            "provider_smoke": _sanitize(_mapping(provider_smoke.get("result"))),
        },
        "formula_version": _sanitize(quality_audit.get("formula_version")),
    }


def render_narrative_data_html(snapshot: dict[str, Any]) -> str:
    summary = _mapping(snapshot.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>真实叙事数据</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>真实叙事数据</h1>",
            '<section class="summary">',
            "<p>来自现有 Narrative Service / FNI artifacts；不在页面内重算评分、热度、质量分或组合指标。</p>",
            _html_kv("正式叙事", summary.get("narrative_count", 0)),
            _html_kv("候选叙事", summary.get("candidate_narrative_count", 0)),
            _html_kv("股票映射", summary.get("stock_mapping_count", 0)),
            _html_kv("证据包", summary.get("evidence_pack_count", 0)),
            _html_kv("质量 scorecard", summary.get("quality_scorecard_count", 0)),
            _html_kv("质量问题", summary.get("quality_issue_count", 0)),
            _html_kv("抽取复核项", summary.get("extraction_issue_count", 0)),
            "</section>",
            _source_table(_list(snapshot.get("source_artifacts"))),
            _narrative_table("正式叙事", _list(snapshot.get("narratives"))),
            _narrative_table("候选叙事", _list(snapshot.get("candidate_narratives"))),
            _scorecard_table(_list(snapshot.get("evidence_pack_scorecards"))),
            _issue_table("质量问题", _list(snapshot.get("quality_issues"))),
            _issue_table("抽取与置信度复核", _list(snapshot.get("extraction_confidence_issues"))),
            _service_health(snapshot),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _load_source(*, project_root: Path, relative_path: str) -> dict[str, Any]:
    path = project_root / relative_path
    if not path.exists():
        return {"path": relative_path, "status": "missing", "payload": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "path": relative_path,
            "status": "invalid_json",
            "error": str(exc),
            "payload": {},
        }
    return {"path": relative_path, "status": "available", "payload": payload}


def _source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    payload = _mapping(source.get("payload"))
    return {
        "path": source.get("path", ""),
        "status": source.get("status", "missing"),
        "version": _sanitize(payload.get("version")),
        "generated_at": _sanitize(payload.get("generated_at")),
        "error": _sanitize(source.get("error", "")),
    }


def _source_table(sources: list[Any]) -> str:
    rows = [_mapping(source) for source in sources]
    header = "".join(f"<th>{_html_text(label)}</th>" for label in ("数据源", "状态", "版本", "生成时间"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('path'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('version'))}</td>"
        f"<td>{_html_text(row.get('generated_at'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>数据来源</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _narrative_table(title: str, rows_raw: list[Any]) -> str:
    rows = [_mapping(row) for row in rows_raw]
    if not rows:
        return f"<section><h2>{_html_text(title)}</h2><p>没有可展示记录。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for label in ("ID", "名称", "状态", "复核状态"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('narrative_id') or row.get('candidate_narrative_id'))}</td>"
        f"<td>{_html_text(row.get('display_name') or row.get('canonical_name_zh') or row.get('name'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('human_review_status'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>{_html_text(title)}</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _scorecard_table(rows_raw: list[Any]) -> str:
    rows = [_mapping(row) for row in rows_raw]
    if not rows:
        return "<section><h2>证据质量 scorecard</h2><p>没有可展示记录。</p></section>"
    header = "".join(
        f"<th>{_html_text(label)}</th>" for label in ("Evidence Pack", "股票", "叙事", "分数", "等级")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('evidence_pack_id') or row.get('pack_id'))}</td>"
        f"<td>{_html_text(row.get('stock_code') or _mapping(row.get('lookup')).get('stock_code'))}</td>"
        f"<td>{_html_text(row.get('narrative_id') or _mapping(row.get('lookup')).get('narrative_id') or row.get('narrative_name'))}</td>"
        f"<td>{_html_text(row.get('quality_score') or row.get('score'))}</td>"
        f"<td>{_html_text(row.get('grade') or row.get('quality_grade'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>证据质量 scorecard</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _issue_table(title: str, rows_raw: list[Any]) -> str:
    rows = [_mapping(row) for row in rows_raw]
    if not rows:
        return f"<section><h2>{_html_text(title)}</h2><p>没有可展示记录。</p></section>"
    header = "".join(f"<th>{_html_text(label)}</th>" for label in ("ID", "状态/严重度", "说明"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('issue_id') or row.get('source_event_id') or row.get('id'))}</td>"
        f"<td>{_html_text(row.get('severity') or row.get('status'))}</td>"
        f"<td>{_html_text(row.get('message') or row.get('issue') or row.get('reason'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>{_html_text(title)}</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _service_health(snapshot: dict[str, Any]) -> str:
    health = _mapping(snapshot.get("service_health"))
    rows = [
        ("Conformance", _mapping(health.get("conformance"))),
        ("Provider smoke", _mapping(health.get("provider_smoke"))),
    ]
    header = "".join(f"<th>{_html_text(label)}</th>" for label in ("检查", "状态", "详情"))
    body = "".join(
        "<tr>"
        f"<td>{_html_text(label)}</td>"
        f"<td>{_html_text(payload.get('status'))}</td>"
        f"<td>{_html_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))}</td>"
        "</tr>"
        for label, payload in rows
    )
    return f"<section><h2>服务健康</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(child)
            for key, child in value.items()
            if not _is_sensitive_key(str(key))
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
