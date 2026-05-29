from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.request import urlopen

from scripts import run_narrative_review_workspace

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "stock-narrative-service"
SRC_ROOT = SERVICE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from stock_narrative_service.app import create_server  # noqa: E402
from stock_narrative_service.config import ServiceConfig  # noqa: E402


def test_direct_cli_bootstraps_repo_root_before_argument_validation(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "run_narrative_review_workspace.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--output-dir",
            str(tmp_path / "workspace"),
        ],
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "--service-url or NARRATIVE_SERVICE_URL is required" in output
    assert "ModuleNotFoundError" not in output


def test_review_workspace_groups_queue_and_links_detail_endpoints():
    workspace = run_narrative_review_workspace.build_review_workspace(
        base_url="http://127.0.0.1:8800",
        queue_payload={
            "summary": {"pending_review": 1, "ready_for_trust_audit": 0},
            "items": [
                {
                    "payload_ref": "C_SEED",
                    "status": "pending_review",
                    "recommended_action": "human_review_required",
                    "missing_gates": ["service_review_approval"],
                }
            ],
        },
        candidate_details={
            "C_SEED": {
                "candidate": {"name": "机器人执行器"},
                "promotion_preflight": {"result": "blocked"},
                "review_history": [],
            }
        },
        evidence_payload={
            "packs": [
                {
                    "stock_code": "600519",
                    "stock_name": "贵州茅台",
                    "proposed_mappings": [
                        {
                            "narrative_id": "N_BAIJIU",
                            "narrative_name": "白酒",
                            "evidence_pack_id": "EPACK_TEST",
                            "candidate_mapping_id": "CMAP_TEST",
                            "trust_status": "candidate_untrusted",
                        }
                    ],
                }
            ]
        },
    )

    assert workspace["groups"]["pending_review"][0]["candidate_narrative_id"] == (
        "C_SEED"
    )
    assert workspace["groups"]["pending_review"][0]["candidate_detail_url"] == (
        "http://127.0.0.1:8800/api/v1/narratives/candidates/C_SEED"
    )
    assert workspace["evidence_links"][0]["evidence_detail_url"] == (
        "http://127.0.0.1:8800/api/v1/narratives/evidence-packs/EPACK_TEST"
    )
    assert workspace["available_actions"] == ["approve", "reject", "defer"]


def test_review_workspace_html_shows_gates_and_action_commands():
    workspace = run_narrative_review_workspace.build_review_workspace(
        base_url="http://127.0.0.1:8800",
        queue_payload={
            "summary": {"approved_blocked_by_evidence": 1},
            "items": [
                {
                    "payload_ref": "C_SEED",
                    "status": "approved_blocked_by_evidence",
                    "recommended_action": "complete_missing_gates",
                    "missing_gates": ["source_evidence"],
                }
            ],
        },
        candidate_details={"C_SEED": {"candidate": {"name": "机器人执行器"}}},
        evidence_payload={"packs": []},
    )

    html = run_narrative_review_workspace.render_html_workspace(workspace)

    assert "候选叙事审核工作台" in html
    assert "approved_blocked_by_evidence" in html
    assert "source_evidence" in html
    assert "approve" in html
    assert "reject" in html
    assert "defer" in html


def test_run_review_workspace_submits_action_and_writes_json_html(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        exit_code = run_narrative_review_workspace.main(
            [
                "--service-url",
                base_url,
                "--output-dir",
                str(tmp_path / "workspace"),
                "--action",
                "approve",
                "--candidate-id",
                "C_SEED",
                "--reviewed-by",
                "test-reviewer",
                "--review-note",
                "Workspace approval.",
            ]
        )
        actions = _get_json(f"{base_url}/api/v1/narratives/review-actions")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    workspace = json.loads(
        (tmp_path / "workspace" / "narrative_review_workspace.json").read_text(
            encoding="utf-8"
        )
    )
    html = (tmp_path / "workspace" / "narrative_review_workspace.html").read_text(
        encoding="utf-8"
    )

    assert exit_code == 0
    assert workspace["action_result"]["decision"]["action"] == "approve"
    assert workspace["groups"]["ready_for_trust_audit"][0]["candidate_narrative_id"] == (
        "C_SEED"
    )
    assert actions["data"]["items"][0]["action"] == "approve"
    assert "候选叙事审核工作台" in html
    assert "C_SEED" in html


def _write_seed_files(tmp_path: Path) -> ServiceConfig:
    registry_path = tmp_path / "registry.json"
    mappings_path = tmp_path / "mappings.json"
    evidence_path = tmp_path / "evidence.json"
    events_path = tmp_path / "events.json"
    intake_ledger_path = tmp_path / "runtime" / "intake_events.json"
    review_actions_path = tmp_path / "runtime" / "review_actions.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": "registry-v1",
                "trust_metadata": {"trust_status": "untrusted_experimental"},
                "narratives": [{"narrative_id": "N_BAIJIU", "name": "白酒"}],
                "candidate_narratives": [
                    {
                        "candidate_narrative_id": "C_SEED",
                        "name": "机器人执行器",
                        "rationale": "Seed candidate has repeatable source support.",
                        "representative_citation_ids": ["SRC_1", "SRC_2"],
                        "exclusion_criteria": ["Do not promote from one stock only."],
                        "human_review_status": "candidate",
                        "trust_status": "candidate_untrusted",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    mappings_path.write_text(
        json.dumps(
            {
                "trust_metadata": {"trust_status": "untrusted_experimental"},
                "mappings": [{"stock_code": "600519", "narrative_id": "N_BAIJIU"}],
            }
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            {
                "version": "mapping-evidence-pack-v0",
                "trust_status": "candidate_untrusted",
                "packs": [
                    {
                        "stock_code": "600519",
                        "stock_name": "贵州茅台",
                        "proposed_mappings": [
                            {
                                "narrative_id": "N_BAIJIU",
                                "narrative_name": "白酒",
                                "trust_status": "candidate_untrusted",
                                "mapping_rationale": "Evidence workspace test.",
                                "evidence_items": [],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    events_path.write_text(
        json.dumps({"version": "candidate-narrative-events-v1", "events": []}),
        encoding="utf-8",
    )
    return ServiceConfig(
        registry_path=registry_path,
        mappings_path=mappings_path,
        evidence_packs_path=evidence_path,
        candidate_events_path=events_path,
        intake_ledger_path=intake_ledger_path,
        review_actions_path=review_actions_path,
    )


def _start(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def _get_json(url: str):
    with urlopen(url, timeout=2) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))
