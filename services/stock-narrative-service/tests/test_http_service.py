from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from urllib.request import Request, urlopen

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SERVICE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from stock_narrative_service.app import create_server  # noqa: E402
from stock_narrative_service.config import ServiceConfig  # noqa: E402


def test_required_get_endpoints_return_normalized_envelopes(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"

        registry = _get_json(f"{base_url}/api/v1/narratives/registry")
        mappings = _get_json(f"{base_url}/api/v1/narratives/mappings")
        evidence = _get_json(f"{base_url}/api/v1/narratives/evidence-packs")
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
        audit = _get_json(f"{base_url}/api/v1/narratives/trust-audits/latest")
        queue = _get_json(f"{base_url}/api/v1/narratives/review-queue")
        ops = _get_json(f"{base_url}/api/v1/narratives/ops/summary")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    for envelope in (registry, mappings, evidence, candidates, audit, queue, ops):
        assert set(envelope) >= {
            "status",
            "source",
            "provider",
            "provider_version",
            "data",
            "warnings",
            "trust_metadata",
        }
        assert envelope["source"] == "narrative_service"
        assert envelope["provider"] == "stock-narrative-service"

    assert registry["data"]["version"] == "registry-v1"
    assert registry["trust_metadata"]["trust_status"] == "untrusted_experimental"
    assert mappings["data"]["mappings"][0]["stock_code"] == "600519"
    assert evidence["data"]["trust_status"] == "candidate_untrusted"
    assert candidates["data"]["candidate_narratives"][0]["candidate_narrative_id"] == "C_SEED"
    assert audit["data"]["result"] == "blocked"
    assert queue["data"]["items"][0]["item_type"] == "candidate_narrative"
    assert ops["data"]["summary"]["candidate_narrative_count"] == 1
    assert ops["data"]["summary"]["stock_mapping_count"] == 1
    assert ops["data"]["review_queue_summary"]["pending_review"] == 1


def test_ops_summary_reflects_review_queue_changes(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        before = _get_json(f"{base_url}/api/v1/narratives/ops/summary")
        _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Ready for summary.",
            },
        )
        after = _get_json(f"{base_url}/api/v1/narratives/ops/summary")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert before["data"]["summary"]["review_action_count"] == 0
    assert before["data"]["review_queue_summary"]["pending_review"] == 1
    assert after["data"]["summary"]["review_action_count"] == 1
    assert after["data"]["review_queue_summary"]["ready_for_trust_audit"] == 1
    assert after["data"]["trust_audit"]["result"] == "blocked"


def test_health_endpoint_is_lightweight(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        health = _get_json(f"{base_url}/api/health")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert health == {
        "status": "ok",
        "service": "stock-narrative-service",
        "provider_version": "v0",
    }


def test_intake_events_create_only_candidate_review_items(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _post_json(
            f"{base_url}/api/v1/narratives/intake/events",
            {
                "events": [
                    {
                        "event_id": "EVT_ROBOT",
                        "source_type": "manual",
                        "event_time": "2026-05-28T10:00:00+08:00",
                        "title": "机器人执行器",
                        "source_url": "manual://robot-actuator",
                        "candidate_narratives": [
                            {
                                "name": "机器人执行器",
                                "canonical_taxonomy": "机器人",
                                "confidence": 0.63,
                            }
                        ],
                    }
                ]
            },
        )
        queue = _get_json(f"{base_url}/api/v1/narratives/review-queue")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    assert response["trust_metadata"]["trust_status"] == "candidate_untrusted"
    created = response["data"]["candidate_narratives"]
    assert created
    assert {item["trust_status"] for item in created} == {"candidate_untrusted"}
    assert {item["human_review_status"] for item in created} == {"candidate"}
    assert "trusted_validated" not in json.dumps(response, ensure_ascii=False)
    assert any(
        item["payload_ref"] == created[0]["candidate_narrative_id"]
        for item in queue["data"]["items"]
    )


def test_review_actions_are_persisted_without_trusted_promotion(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Looks structurally valid, but not trusted.",
            },
        )
        actions = _get_json(f"{base_url}/api/v1/narratives/review-actions")
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    assert response["trust_metadata"]["trust_status"] == "candidate_untrusted"
    assert response["data"]["decision"]["action"] == "approve"
    assert response["data"]["decision"]["promotion_effect"] == "none"
    assert actions["data"]["items"][0]["candidate_narrative_id"] == "C_SEED"
    assert actions["data"]["items"][0]["action"] == "approve"
    assert candidates["data"]["candidate_narratives"][0]["human_review_status"] == "candidate"
    assert candidates["data"]["candidate_narratives"][0]["trust_status"] == (
        "candidate_untrusted"
    )
    assert "trusted_validated" not in json.dumps(response, ensure_ascii=False)
    assert "trusted_validated" not in json.dumps(actions, ensure_ascii=False)


def test_review_actions_are_append_only_and_do_not_mutate_trusted_sources(tmp_path):
    config = _write_seed_files(tmp_path)
    source_snapshots = {
        config.registry_path: config.registry_path.read_text(encoding="utf-8"),
        config.mappings_path: config.mappings_path.read_text(encoding="utf-8"),
        config.evidence_packs_path: config.evidence_packs_path.read_text(
            encoding="utf-8"
        ),
    }
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        first = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "First ledger decision.",
                "source_metadata": {
                    "source": "review-workspace",
                    "request_id": "REQ_APPEND_1",
                },
            },
        )
        second = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "defer",
                "reviewed_by": "test-reviewer",
                "review_note": "Second ledger decision.",
                "source_metadata": {
                    "source": "review-workspace",
                    "request_id": "REQ_APPEND_2",
                },
            },
        )
        actions = _get_json(f"{base_url}/api/v1/narratives/review-actions")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert first["data"]["decision"]["ledger_record_type"] == "review_action"
    assert first["data"]["decision"]["ledger_sequence"] == 1
    assert first["data"]["decision"]["source_metadata"] == {
        "source": "review-workspace",
        "request_id": "REQ_APPEND_1",
    }
    assert second["data"]["decision"]["ledger_sequence"] == 2
    assert actions["data"]["version"] == "narrative-review-actions-v1"
    assert [item["ledger_sequence"] for item in actions["data"]["items"]] == [1, 2]
    assert actions["data"]["items"][0]["review_note"] == "First ledger decision."
    assert actions["data"]["items"][1]["review_note"] == "Second ledger decision."
    for path, before_text in source_snapshots.items():
        assert path.read_text(encoding="utf-8") == before_text


def test_failed_intake_payload_does_not_create_ledger_or_negative_cache(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        before = _get_json(f"{base_url}/api/v1/narratives/candidates")
        try:
            _post_json(
                f"{base_url}/api/v1/narratives/intake/events",
                {"events": ["not-an-event-object"]},
            )
        except Exception as exc:
            assert "HTTP Error 400" in str(exc)
        else:
            raise AssertionError("expected 400 for invalid event payload")
        after = _get_json(f"{base_url}/api/v1/narratives/candidates")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert before["data"] == after["data"]
    assert not config.intake_ledger_path.exists()


def test_duplicate_intake_replays_append_events_but_dedupes_candidate_reads(tmp_path):
    config = _write_seed_files(tmp_path)
    event = {
        "event_id": "EVT_DUPLICATE",
        "source_type": "manual",
        "event_time": "2026-05-28T10:00:00+08:00",
        "title": "重复候选",
        "source_url": "manual://duplicate",
        "source_metadata": {"provider": "manual", "permission": "internal_review"},
        "candidate_narratives": [
            {
                "candidate_narrative_id": "C_DUPLICATE",
                "name": "重复候选",
                "canonical_taxonomy": "测试",
                "confidence": 0.5,
            }
        ],
    }
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        _post_json(f"{base_url}/api/v1/narratives/intake/events", {"events": [event]})
        _post_json(f"{base_url}/api/v1/narratives/intake/events", {"events": [event]})
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    ledger = json.loads(config.intake_ledger_path.read_text(encoding="utf-8"))
    duplicate_candidates = [
        item
        for item in candidates["data"]["candidate_narratives"]
        if item["candidate_narrative_id"] == "C_DUPLICATE"
    ]
    assert ledger["version"] == "service-intake-events-v1"
    assert [item["ledger_sequence"] for item in ledger["events"]] == [1, 2]
    assert {item["ledger_record_type"] for item in ledger["events"]} == {
        "candidate_intake_event"
    }
    assert ledger["events"][0]["source_metadata"] == {
        "provider": "manual",
        "permission": "internal_review",
    }
    assert len(duplicate_candidates) == 1
    assert duplicate_candidates[0]["source_event_ids"] == ["EVT_DUPLICATE"]


def test_review_queue_reflects_latest_review_action_and_preflight_state(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        pending = _get_json(f"{base_url}/api/v1/narratives/review-queue")
        _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Ready for trust audit.",
            },
        )
        ready = _get_json(f"{base_url}/api/v1/narratives/review-queue")
        filtered = _get_json(
            f"{base_url}/api/v1/narratives/review-queue?status=ready_for_trust_audit"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert pending["data"]["items"][0]["status"] == "pending_review"
    assert pending["data"]["items"][0]["recommended_action"] == (
        "human_review_required"
    )
    assert pending["data"]["summary"]["pending_review"] == 1
    assert ready["data"]["items"][0]["status"] == "ready_for_trust_audit"
    assert ready["data"]["items"][0]["recommended_action"] == "run_trust_audit"
    assert ready["data"]["items"][0]["preflight_result"] == "ready_for_trust_audit"
    assert ready["data"]["summary"]["ready_for_trust_audit"] == 1
    assert filtered["data"]["filter"]["status"] == "ready_for_trust_audit"
    assert len(filtered["data"]["items"]) == 1


def test_review_queue_can_filter_rejected_items(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "reject",
                "reviewed_by": "test-reviewer",
                "review_note": "Not a durable narrative.",
            },
        )
        rejected = _get_json(
            f"{base_url}/api/v1/narratives/review-queue?status=rejected"
        )
        pending = _get_json(
            f"{base_url}/api/v1/narratives/review-queue?status=pending_review"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert rejected["data"]["items"][0]["status"] == "rejected"
    assert rejected["data"]["items"][0]["recommended_action"] == "no_action"
    assert rejected["data"]["summary"]["rejected"] == 1
    assert pending["data"]["items"] == []


def test_review_action_rejects_unknown_candidate(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            _post_json(
                f"{base_url}/api/v1/narratives/review-actions",
                {
                    "candidate_narrative_id": "C_UNKNOWN",
                    "action": "reject",
                    "reviewed_by": "test-reviewer",
                    "review_note": "unknown candidate",
                },
            )
        except Exception as exc:
            assert "HTTP Error 400" in str(exc)
        else:
            raise AssertionError("expected 400 for unknown candidate")
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_promotion_preflight_blocks_until_review_action_exists(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        blocked = _post_json(
            f"{base_url}/api/v1/narratives/promotion/preflight",
            {"candidate_narrative_id": "C_SEED"},
        )
        _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Approved for audit preflight.",
            },
        )
        ready = _post_json(
            f"{base_url}/api/v1/narratives/promotion/preflight",
            {"candidate_narrative_id": "C_SEED"},
        )
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert blocked["data"]["result"] == "blocked"
    assert "service_review_approval" in blocked["data"]["missing_gates"]
    assert blocked["data"]["promotion_effect"] == "none"
    assert ready["data"]["result"] == "ready_for_trust_audit"
    assert ready["data"]["missing_gates"] == []
    assert ready["data"]["promotion_effect"] == "none"
    assert candidates["data"]["candidate_narratives"][0]["trust_status"] == (
        "candidate_untrusted"
    )
    assert "trusted_validated" not in json.dumps(ready, ensure_ascii=False)


def test_promotion_preflight_rejects_unknown_candidate(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            _post_json(
                f"{base_url}/api/v1/narratives/promotion/preflight",
                {"candidate_narrative_id": "C_UNKNOWN"},
            )
        except Exception as exc:
            assert "HTTP Error 400" in str(exc)
        else:
            raise AssertionError("expected 400 for unknown candidate")
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_unknown_route_returns_error_envelope(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            _get_json(f"{base_url}/api/v1/narratives/missing")
        except Exception as exc:
            assert "HTTP Error 404" in str(exc)
        else:
            raise AssertionError("expected 404 for unknown route")
    finally:
        server.shutdown()
        thread.join(timeout=2)


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
                "trust_metadata": {
                    "trust_status": "untrusted_experimental",
                    "trust_note": "seed data",
                },
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
                "trust_metadata": {
                    "trust_status": "untrusted_experimental",
                    "trust_note": "seed mappings",
                },
                "mappings": [
                    {
                        "stock_code": "600519",
                        "narrative_id": "N_BAIJIU",
                        "confidence": 0.86,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps(
            {
                "version": "mapping-evidence-pack-v0",
                "trust_status": "candidate_untrusted",
                "packs": [],
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


def _post_json(url: str, payload: dict):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=2) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))
