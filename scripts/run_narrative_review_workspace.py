from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402

DEFAULT_WORKSPACE_DIR = DEFAULT_OUTPUT_DIR / "narrative_review_workspace"
REVIEW_ACTIONS = ("approve", "reject", "defer")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a Narrative Service human review workspace."
    )
    parser.add_argument("--service-url", default=os.environ.get("NARRATIVE_SERVICE_URL", ""))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_WORKSPACE_DIR)
    parser.add_argument("--action", choices=REVIEW_ACTIONS)
    parser.add_argument("--candidate-id")
    parser.add_argument("--reviewed-by")
    parser.add_argument("--review-note")
    parser.add_argument("--idempotency-key")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_url = args.service_url.strip().rstrip("/")
    if not base_url:
        raise SystemExit("--service-url or NARRATIVE_SERVICE_URL is required")
    action_result = None
    if args.action:
        action_result = submit_review_action(
            base_url=base_url,
            candidate_id=args.candidate_id or "",
            action=args.action,
            reviewed_by=args.reviewed_by or "",
            review_note=args.review_note or "",
            idempotency_key=args.idempotency_key or "",
        )
    workspace = fetch_review_workspace(base_url=base_url, action_result=action_result)
    write_workspace(output_dir=args.output_dir, workspace=workspace)
    print(
        json.dumps(
            {
                "json": str(args.output_dir / "narrative_review_workspace.json"),
                "html": str(args.output_dir / "narrative_review_workspace.html"),
                "candidate_count": workspace["summary"]["candidate_count"],
                "action_status": "submitted" if action_result else "not_submitted",
            },
            ensure_ascii=False,
        )
    )
    return 0


def submit_review_action(
    *,
    base_url: str,
    candidate_id: str,
    action: str,
    reviewed_by: str,
    review_note: str,
    idempotency_key: str = "",
) -> dict[str, Any]:
    if not candidate_id:
        raise ValueError("--candidate-id is required when --action is set")
    if not reviewed_by:
        raise ValueError("--reviewed-by is required when --action is set")
    if not review_note:
        raise ValueError("--review-note is required when --action is set")
    payload = {
        "candidate_narrative_id": candidate_id,
        "action": action,
        "reviewed_by": reviewed_by,
        "review_note": review_note,
    }
    if idempotency_key:
        payload["idempotency_key"] = idempotency_key
    response = _request_json(
        method="POST",
        url=_endpoint(base_url, "/api/v1/narratives/review-actions"),
        payload=payload,
    )
    return _mapping(response.get("data"))


def fetch_review_workspace(
    *,
    base_url: str,
    action_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    queue = _request_json(
        method="GET",
        url=_endpoint(base_url, "/api/v1/narratives/review-queue"),
    )["data"]
    evidence = _request_json(
        method="GET",
        url=_endpoint(base_url, "/api/v1/narratives/evidence-packs"),
    )["data"]
    candidate_details = {
        candidate_id: _request_json(
            method="GET",
            url=_endpoint(
                base_url,
                f"/api/v1/narratives/candidates/{quote(candidate_id)}",
            ),
        )["data"]
        for candidate_id in _queue_candidate_ids(queue)
    }
    return build_review_workspace(
        base_url=base_url,
        queue_payload=queue,
        candidate_details=candidate_details,
        evidence_payload=evidence,
        action_result=action_result,
    )


def build_review_workspace(
    *,
    base_url: str,
    queue_payload: dict[str, Any],
    candidate_details: dict[str, dict[str, Any]],
    evidence_payload: dict[str, Any],
    action_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in _list(queue_payload.get("items")):
        candidate_id = str(item.get("payload_ref") or "")
        detail = candidate_details.get(candidate_id, {})
        status = str(item.get("status") or "unknown")
        groups.setdefault(status, []).append(
            {
                "candidate_narrative_id": candidate_id,
                "candidate_name": str(
                    _mapping(detail.get("candidate")).get("name") or candidate_id
                ),
                "status": status,
                "recommended_action": str(item.get("recommended_action") or ""),
                "missing_gates": _strings(item.get("missing_gates")),
                "preflight_result": str(item.get("preflight_result") or ""),
                "candidate_detail_url": _endpoint(
                    base_url,
                    f"/api/v1/narratives/candidates/{quote(candidate_id)}",
                ),
                "review_history_count": len(_list(detail.get("review_history"))),
            }
        )
    evidence_links = _evidence_links(base_url=base_url, evidence_payload=evidence_payload)
    return {
        "version": "narrative-review-workspace-v1",
        "generated_at": _now(),
        "base_url": base_url,
        "summary": {
            **_mapping(queue_payload.get("summary")),
            "candidate_count": sum(len(items) for items in groups.values()),
            "evidence_link_count": len(evidence_links),
        },
        "groups": groups,
        "evidence_links": evidence_links,
        "available_actions": list(REVIEW_ACTIONS),
        "action_endpoint": _endpoint(base_url, "/api/v1/narratives/review-actions"),
        "action_result": action_result or {},
    }


def render_html_workspace(workspace: dict[str, Any]) -> str:
    group_sections = []
    for status, items in _mapping(workspace.get("groups")).items():
        group_sections.append(f"<section><h2>{_html(status)}</h2>")
        if not items:
            group_sections.append('<p class="empty">无候选项</p>')
        for item in _list(items):
            group_sections.append(
                '<article class="candidate">'
                f"<h3>{_html(item.get('candidate_name'))}</h3>"
                f"<p><strong>ID:</strong> {_html(item.get('candidate_narrative_id'))}</p>"
                f"<p><strong>建议动作:</strong> {_html(item.get('recommended_action'))}</p>"
                f"<p><strong>缺失门槛:</strong> {_html(', '.join(_strings(item.get('missing_gates'))) or '-')}</p>"
                f"<p><a href=\"{_html(item.get('candidate_detail_url'))}\">打开候选详情</a></p>"
                "</article>"
            )
        group_sections.append("</section>")
    evidence_rows = [
        "<tr>"
        f"<td>{_html(item.get('stock_code'))}</td>"
        f"<td>{_html(item.get('narrative_name'))}</td>"
        f"<td>{_html(item.get('trust_status'))}</td>"
        f"<td><a href=\"{_html(item.get('evidence_detail_url'))}\">打开证据详情</a></td>"
        "</tr>"
        for item in _list(workspace.get("evidence_links"))
    ]
    action_endpoint = str(workspace.get("action_endpoint") or "")
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>候选叙事审核工作台</title>",
            "<style>",
            _styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>候选叙事审核工作台</h1>",
            f"<p>生成时间: {_html(workspace.get('generated_at'))}</p>",
            "<section><h2>操作入口</h2>",
            f"<p>Review action endpoint: <code>{_html(action_endpoint)}</code></p>",
            "<p>Actions: <code>approve</code> <code>reject</code> <code>defer</code></p>",
            "</section>",
            *group_sections,
            "<section><h2>证据详情入口</h2>",
            "<table><thead><tr><th>股票</th><th>叙事</th><th>状态</th><th>链接</th></tr></thead><tbody>",
            *(evidence_rows or ['<tr><td colspan="4">无证据详情</td></tr>']),
            "</tbody></table>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def write_workspace(*, output_dir: Path, workspace: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "narrative_review_workspace.json").write_text(
        json.dumps(workspace, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "narrative_review_workspace.html").write_text(
        render_html_workspace(workspace),
        encoding="utf-8",
    )


def _evidence_links(*, base_url: str, evidence_payload: dict[str, Any]) -> list[dict[str, Any]]:
    links = []
    for pack in _list(evidence_payload.get("packs")):
        for mapping in _list(pack.get("proposed_mappings")):
            evidence_pack_id = str(mapping.get("evidence_pack_id") or "")
            links.append(
                {
                    "stock_code": str(pack.get("stock_code") or ""),
                    "stock_name": str(pack.get("stock_name") or ""),
                    "narrative_id": str(mapping.get("narrative_id") or ""),
                    "narrative_name": str(mapping.get("narrative_name") or ""),
                    "trust_status": str(mapping.get("trust_status") or ""),
                    "evidence_pack_id": evidence_pack_id,
                    "candidate_mapping_id": str(mapping.get("candidate_mapping_id") or ""),
                    "evidence_detail_url": _endpoint(
                        base_url,
                        f"/api/v1/narratives/evidence-packs/{quote(evidence_pack_id)}",
                    ),
                }
            )
    return links


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310
        response_payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(response_payload, dict):
        raise ValueError("response must be a JSON object")
    return response_payload


def _queue_candidate_ids(queue_payload: dict[str, Any]) -> list[str]:
    return [
        str(item.get("payload_ref") or "")
        for item in _list(queue_payload.get("items"))
        if item.get("payload_ref")
    ]


def _endpoint(base_url: str, path: str) -> str:
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _html(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _styles() -> str:
    return """
body { margin: 0; background: #f7f8fa; color: #20242b; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 28px; }
section { background: #fff; border: 1px solid #d9dee7; padding: 16px; margin: 14px 0; }
.candidate { border-top: 1px solid #e4e8ef; padding: 12px 0; }
table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #e4e8ef; padding: 8px; text-align: left; }
code { background: #eef2f7; padding: 2px 5px; }
a { color: #155eef; }
"""


if __name__ == "__main__":
    raise SystemExit(main())
