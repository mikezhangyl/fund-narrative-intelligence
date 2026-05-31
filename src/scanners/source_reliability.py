from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "config" / "source_reliability_scoring.json"


def load_source_reliability_scoring_policy(
    path: Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score_source_reliability(
    source: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_policy = policy or load_source_reliability_scoring_policy()
    score = _weighted_score(_mapping(source.get("dimension_scores")), policy=active_policy)
    warnings: list[str] = []
    if _is_social(source) and not bool(source.get("corroborating_evidence")):
        warnings.append("social_sources_require_corroboration_for_trusted_fact")
    label = _label(source, score=score, warnings=warnings, policy=active_policy)
    display_allowed = label != "Avoid"
    return {
        "source_id": str(source.get("source_id") or ""),
        "display_name": str(source.get("display_name") or ""),
        "source_class": str(source.get("source_class") or ""),
        "score": round(score, 4),
        "label": label,
        "display_allowed": display_allowed,
        "trusted_fact_allowed": label == "Trusted Fact",
        "dimension_scores": _dimension_scores(source, active_policy),
        "warnings": warnings,
        "rationale": _rationale(source, label=label, score=score, warnings=warnings),
    }


def score_source_reliability_inventory(
    inventory: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_policy = policy or load_source_reliability_scoring_policy()
    scores = [
        score_source_reliability(source, policy=active_policy)
        for source in _list(inventory.get("sources"))
    ]
    label_counts = Counter(score["label"] for score in scores)
    return {
        "version": "source-reliability-report-v1",
        "policy_version": str(active_policy.get("version") or ""),
        "generated_at": _utc_now(),
        "summary": {
            "source_count": len(scores),
            "label_counts": {
                label: int(label_counts.get(label, 0))
                for label in _strings(active_policy.get("labels"))
            },
        },
        "scores": scores,
        "dimensions": _strings(active_policy.get("dimensions")),
    }


def render_source_reliability_html(report: dict[str, Any]) -> str:
    summary = _mapping(report.get("summary"))
    rows = "\n".join(_score_rows(report.get("scores")))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>来源可靠性评分报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; }}
    .meta {{ line-height: 1.6; color: #4b5563; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 13px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>来源可靠性评分报告</h1>
  <div class="meta">
    <div>Policy：<code>{_html_text(report.get("policy_version"))}</code></div>
    <div>来源数：<code>{summary.get("source_count", 0)}</code></div>
    <div>标签统计：{_html_text(json.dumps(summary.get("label_counts"), ensure_ascii=False))}</div>
  </div>
  <table>
    <thead><tr><th>source_id</th><th>source_class</th><th>score</th><th>label</th><th>display</th><th>warnings</th><th>rationale</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def _score_rows(value: Any) -> list[str]:
    rows = []
    for score in _list(value):
        rows.append(
            "      <tr>"
            f"<td><code>{_html_text(score.get('source_id'))}</code></td>"
            f"<td>{_html_text(score.get('source_class'))}</td>"
            f"<td>{_html_text(score.get('score'))}</td>"
            f"<td><code>{_html_text(score.get('label'))}</code></td>"
            f"<td>{_html_text(score.get('display_allowed'))}</td>"
            f"<td>{_html_text(' | '.join(_strings(score.get('warnings'))))}</td>"
            f"<td>{_html_text(score.get('rationale'))}</td>"
            "</tr>"
        )
    return rows


def _weighted_score(dimension_scores: dict[str, Any], *, policy: dict[str, Any]) -> float:
    weights = _mapping(policy.get("weights"))
    total_weight = sum(float(weights.get(dimension, 0.0)) for dimension in weights)
    if total_weight <= 0:
        return 0.0
    total = 0.0
    for dimension, weight in weights.items():
        total += _bounded_float(dimension_scores.get(dimension, 0.0)) * float(weight)
    return total / total_weight


def _label(
    source: dict[str, Any],
    *,
    score: float,
    warnings: list[str],
    policy: dict[str, Any],
) -> str:
    if str(source.get("governance_gate_status") or "") == "blocked":
        return str(policy.get("blocked_label") or "Avoid")
    if str(source.get("anti_bot_risk") or "") == "high":
        return str(policy.get("blocked_label") or "Avoid")
    thresholds = _mapping(policy.get("label_thresholds"))
    if _is_social(source) and "social_sources_require_corroboration_for_trusted_fact" in warnings:
        return str(policy.get("social_without_corroboration_label") or "Heat Signal")
    if (
        str(source.get("source_class") or "") == "official_disclosure"
        and score >= float(thresholds.get("trusted_fact", 0.78))
    ):
        return "Trusted Fact"
    if (
        str(source.get("source_class") or "") == "licensed_news"
        and score >= float(thresholds.get("licensed_news", 0.68))
    ):
        return "Licensed News"
    if score >= float(thresholds.get("research_context", 0.55)):
        return "Research Context"
    if score >= float(thresholds.get("experimental", 0.35)):
        return "Experimental"
    return "Avoid"


def _rationale(
    source: dict[str, Any],
    *,
    label: str,
    score: float,
    warnings: list[str],
) -> str:
    if label == "Avoid":
        return "Blocked by governance gate or high acquisition risk."
    if warnings:
        return "; ".join(warnings)
    return f"{source.get('source_class')} scored {score:.2f} with deterministic source dimensions."


def _dimension_scores(source: dict[str, Any], policy: dict[str, Any]) -> dict[str, float]:
    raw = _mapping(source.get("dimension_scores"))
    return {
        dimension: _bounded_float(raw.get(dimension, 0.0))
        for dimension in _strings(policy.get("dimensions"))
    }


def _is_social(source: dict[str, Any]) -> bool:
    return str(source.get("source_class") or "") == "social_community"


def _bounded_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, number))


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
