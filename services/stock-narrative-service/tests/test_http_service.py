from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
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


def test_ops_summary_includes_operational_diagnostics(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/ops/summary")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    diagnostics = response["data"]["diagnostics"]

    assert diagnostics["schema_version"] == "narrative-operational-diagnostics-v1"
    assert diagnostics["provider_source"] == {
        "source": "narrative_service",
        "provider": "stock-narrative-service",
        "provider_version": "v0",
        "data_fetch_mode": "json_file_ledgers_v1",
        "fallback_source": "local_prototype",
    }
    assert diagnostics["status_summary"]["status"] == "available_with_data_gaps"
    assert diagnostics["status_summary"]["product_data_gap_count"] == 1
    assert diagnostics["status_summary"]["system_failure_count"] == 0
    assert diagnostics["status_summary"]["warning_count"] == 0
    assert diagnostics["product_data_gaps"] == [
        {
            "code": "EVIDENCE_PACKS_EMPTY",
            "message": "No evidence packs are currently available.",
            "scope": "evidence_packs",
        }
    ]
    assert diagnostics["system_failures"] == []
    assert diagnostics["queue_summary"] == response["data"]["review_queue_summary"]
    assert diagnostics["audit_status"] == response["data"]["trust_audit"]["result"]


def test_runtime_failure_returns_classified_diagnostics_warning(tmp_path):
    config = _write_seed_files(tmp_path)
    config = ServiceConfig(
        registry_path=tmp_path / "missing-registry.json",
        mappings_path=config.mappings_path,
        evidence_packs_path=config.evidence_packs_path,
        candidate_events_path=config.candidate_events_path,
        intake_ledger_path=config.intake_ledger_path,
        review_actions_path=config.review_actions_path,
        promotion_decisions_path=config.promotion_decisions_path,
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json_error(f"{base_url}/api/v1/narratives/registry")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "degraded"
    assert response["warnings"] == [
        {
            "code": "SERVICE_ERROR",
            "message": response["data"]["error"]["message"],
            "classification": "system_failure",
        }
    ]
    assert response["diagnostics"]["status_summary"] == {
        "status": "degraded",
        "warning_count": 1,
        "product_data_gap_count": 0,
        "system_failure_count": 1,
    }
    assert response["diagnostics"]["system_failures"][0]["code"] == "SERVICE_ERROR"
    assert response["diagnostics"]["product_data_gaps"] == []


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


def test_intake_records_provider_aware_supported_source_types(tmp_path):
    config = _write_seed_files(tmp_path)
    events = [
        {
            "event_id": "EVT_NEWS",
            "source_type": "news",
            "event_time": "2026-05-28T10:00:00+08:00",
            "title": "News-driven robotics signal",
            "source_url": "gateway://news/robotics",
            "provider": "gateway_news_briefs",
            "provider_version": "2026-05",
            "permission_status": "licensed",
            "degradation_state": "available",
            "candidate_narratives": [
                {
                    "candidate_narrative_id": "C_NEWS",
                    "name": "Robotics news signal",
                    "canonical_taxonomy": "robotics",
                    "confidence": 0.61,
                }
            ],
        },
        {
            "event_id": "EVT_ANNOUNCEMENT",
            "source_type": "announcement",
            "event_time": "2026-05-28T10:01:00+08:00",
            "title": "Announcement-driven robotics signal",
            "source_url": "gateway://announcements/robotics",
            "source_metadata": {
                "provider": "tushare_announcements",
                "provider_version": "2026-05",
                "permission_status": "licensed",
                "degradation_state": "available",
            },
            "candidate_narratives": [
                {
                    "candidate_narrative_id": "C_ANNOUNCEMENT",
                    "name": "Robotics announcement signal",
                    "canonical_taxonomy": "robotics",
                    "confidence": 0.62,
                }
            ],
        },
        {
            "event_id": "EVT_MANUAL",
            "source_type": "manual",
            "event_time": "2026-05-28T10:02:00+08:00",
            "title": "Manual robotics signal",
            "source_url": "manual://robotics",
            "provider": "manual_research_note",
            "provider_version": "v1",
            "permission_status": "internal_review",
            "degradation_state": "available",
            "candidate_narratives": [
                {
                    "candidate_narrative_id": "C_MANUAL",
                    "name": "Manual robotics signal",
                    "canonical_taxonomy": "robotics",
                    "confidence": 0.63,
                }
            ],
        },
        {
            "event_id": "EVT_SOCIAL_FUTURE",
            "source_type": "social_future",
            "event_time": "2026-05-28T10:03:00+08:00",
            "title": "Reserved social signal",
            "source_url": "social-future://robotics",
            "provider": "reserved_social_connector",
            "provider_version": "reserved",
            "permission_status": "not_enabled",
            "degradation_state": "reserved",
            "candidate_narratives": [
                {
                    "candidate_narrative_id": "C_SOCIAL_FUTURE",
                    "name": "Reserved social robotics signal",
                    "canonical_taxonomy": "robotics",
                    "confidence": 0.41,
                }
            ],
        },
    ]
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _post_json(
            f"{base_url}/api/v1/narratives/intake/events",
            {"events": events},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    ledger = json.loads(config.intake_ledger_path.read_text(encoding="utf-8"))
    created = response["data"]["candidate_narratives"]
    records_by_type = {record["source_type"]: record for record in ledger["events"]}

    assert response["status"] == "available"
    assert response["trust_metadata"]["trust_status"] == "candidate_untrusted"
    assert {item["candidate_narrative_id"] for item in created} == {
        "C_NEWS",
        "C_ANNOUNCEMENT",
        "C_MANUAL",
        "C_SOCIAL_FUTURE",
    }
    assert {item["trust_status"] for item in created} == {"candidate_untrusted"}
    assert set(records_by_type) == {
        "news",
        "announcement",
        "manual",
        "social_future",
    }
    assert records_by_type["news"]["source_metadata"]["provider"] == (
        "gateway_news_briefs"
    )
    assert records_by_type["announcement"]["source_metadata"]["provider"] == (
        "tushare_announcements"
    )
    for record in ledger["events"]:
        assert record["promotion_effect"] == "none"
        assert set(record["source_metadata"]) >= {
            "provider",
            "provider_version",
            "permission_status",
            "degradation_state",
            "provider_preference",
            "source_mode",
        }
    assert records_by_type["news"]["source_metadata"]["provider_preference"][:2] == [
        "gateway_news_briefs",
        "tushare_news",
    ]
    assert records_by_type["announcement"]["source_metadata"][
        "provider_preference"
    ][:2] == ["gateway_announcements", "tushare_announcements"]
    assert "trusted_validated" not in json.dumps(response, ensure_ascii=False)


def test_intake_reinforces_existing_narrative_without_trusted_promotion(tmp_path):
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
        response = _post_json(
            f"{base_url}/api/v1/narratives/intake/events",
            {
                "events": [
                    {
                        "event_id": "EVT_NEWS_REINFORCEMENT",
                        "source_type": "news",
                        "event_time": "2026-05-28T10:00:00+08:00",
                        "title": "Baijiu channel news",
                        "source_url": "gateway://news/baijiu-channel",
                        "provider": "gateway_news_briefs",
                        "provider_version": "2026-05",
                        "permission_status": "licensed",
                        "degradation_state": "available",
                        "reinforces_narrative_ids": ["N_BAIJIU"],
                        "supported_claim_types": [
                            "business_relevance",
                            "near_term_catalyst",
                        ],
                    }
                ]
            },
        )
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    reinforcement = response["data"]["evidence_reinforcements"][0]
    assert response["trust_metadata"]["trust_status"] == "candidate_untrusted"
    assert response["data"]["candidate_narratives"] == []
    assert reinforcement["narrative_id"] == "N_BAIJIU"
    assert reinforcement["source_event_id"] == "EVT_NEWS_REINFORCEMENT"
    assert reinforcement["trust_status"] == "candidate_untrusted"
    assert reinforcement["promotion_effect"] == "none"
    assert reinforcement["source_metadata"]["provider"] == "gateway_news_briefs"
    assert reinforcement["source_metadata"]["permission_status"] == "licensed"
    assert reinforcement["source_metadata"]["degradation_state"] == "available"
    assert reinforcement["supported_claim_types"] == [
        "business_relevance",
        "near_term_catalyst",
    ]
    assert "trusted_validated" not in json.dumps(response, ensure_ascii=False)
    assert candidates["data"]["candidate_narratives"] == [
        {
            "candidate_narrative_id": "C_SEED",
            "name": "机器人执行器",
            "rationale": "Seed candidate has repeatable source support.",
            "representative_citation_ids": ["SRC_1", "SRC_2"],
            "exclusion_criteria": ["Do not promote from one stock only."],
            "human_review_status": "candidate",
            "trust_status": "candidate_untrusted",
        }
    ]
    for path, before_text in source_snapshots.items():
        assert path.read_text(encoding="utf-8") == before_text


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
    assert ledger["events"][0]["source_metadata"]["provider"] == "manual"
    assert ledger["events"][0]["source_metadata"]["permission"] == "internal_review"
    assert ledger["events"][0]["source_metadata"]["permission_status"] == (
        "internal_review"
    )
    assert len(duplicate_candidates) == 1
    assert duplicate_candidates[0]["source_event_ids"] == ["EVT_DUPLICATE"]


def test_intake_fallback_identity_is_stable_for_links_and_duplicate_reads(tmp_path):
    config = _write_seed_files(tmp_path)
    event = {
        "source_type": "manual",
        "event_time": "2026-05-28T10:00:00+08:00",
        "title": "稳定候选身份",
        "source_url": "manual://stable-identity",
        "candidate_narratives": [
            {
                "name": "稳定候选身份",
                "canonical_taxonomy": "身份测试",
                "confidence": 0.7,
            }
        ],
    }
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        first = _post_json(
            f"{base_url}/api/v1/narratives/intake/events",
            {"events": [event]},
        )
        second = _post_json(
            f"{base_url}/api/v1/narratives/intake/events",
            {"events": [event]},
        )
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    first_candidate = first["data"]["candidate_narratives"][0]
    second_candidate = second["data"]["candidate_narratives"][0]
    matching_candidates = [
        item
        for item in candidates["data"]["candidate_narratives"]
        if item["candidate_narrative_id"] == first_candidate["candidate_narrative_id"]
    ]
    ledger = json.loads(config.intake_ledger_path.read_text(encoding="utf-8"))

    assert first_candidate["candidate_narrative_id"].startswith("C_INTAKE_")
    assert first_candidate["candidate_narrative_id"] == second_candidate[
        "candidate_narrative_id"
    ]
    assert first_candidate["identity_metadata"] == {
        "id_source": "deterministic_fallback",
        "id_fields": ["name", "canonical_taxonomy"],
    }
    assert [event["event_id"] for event in ledger["events"]] == [
        first_candidate["source_event_ids"][0],
        first_candidate["source_event_ids"][0],
    ]
    assert len(matching_candidates) == 1
    assert matching_candidates[0]["source_event_ids"] == [
        first_candidate["source_event_ids"][0]
    ]


def test_review_action_idempotency_key_replays_without_append(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        payload = {
            "candidate_narrative_id": "C_SEED",
            "action": "approve",
            "reviewed_by": "test-reviewer",
            "review_note": "Idempotent approval.",
            "idempotency_key": "IDEMPOTENT_APPROVE_1",
        }
        first = _post_json(f"{base_url}/api/v1/narratives/review-actions", payload)
        second = _post_json(f"{base_url}/api/v1/narratives/review-actions", payload)
        actions = _get_json(f"{base_url}/api/v1/narratives/review-actions")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert first["data"]["decision"]["review_action_id"] == second["data"]["decision"][
        "review_action_id"
    ]
    assert first["data"]["decision"]["idempotency_key"] == "IDEMPOTENT_APPROVE_1"
    assert second["data"]["decision"]["idempotent_replay"] is True
    assert len(actions["data"]["items"]) == 1
    assert actions["data"]["items"][0]["ledger_sequence"] == 1


def test_evidence_packs_expose_stable_pack_and_mapping_ids(tmp_path):
    config = _write_seed_files(tmp_path)
    evidence = json.loads(config.evidence_packs_path.read_text(encoding="utf-8"))
    evidence["packs"] = [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "proposed_mappings": [
                {
                    "narrative_id": "N_BAIJIU",
                    "narrative_name": "白酒",
                    "trust_status": "candidate_untrusted",
                    "mapping_rationale": "身份测试映射。",
                    "evidence_items": [],
                }
            ],
        }
    ]
    config.evidence_packs_path.write_text(json.dumps(evidence), encoding="utf-8")
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/evidence-packs")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    mapping = response["data"]["packs"][0]["proposed_mappings"][0]
    assert mapping["evidence_pack_id"].startswith("EPACK_")
    assert mapping["candidate_mapping_id"].startswith("CMAP_")
    assert mapping["identity_metadata"] == {
        "id_source": "deterministic_fallback",
        "id_fields": ["stock_code", "narrative_id"],
    }


def test_evidence_pack_detail_by_stock_and_narrative_returns_source_drilldown(tmp_path):
    config = _write_seed_files(tmp_path)
    _write_detail_evidence_pack(config)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(
            f"{base_url}/api/v1/narratives/evidence-packs/detail"
            "?stock_code=600519&narrative_id=N_BAIJIU"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    assert response["trust_metadata"]["trust_status"] == "candidate_untrusted"
    payload = response["data"]
    assert payload["version"] == "mapping-evidence-pack-detail-v1"
    assert payload["lookup"] == {
        "evidence_pack_id": payload["evidence_pack_id"],
        "stock_code": "600519",
        "narrative_id": "N_BAIJIU",
    }
    assert payload["mapping_rationale"] == "主营产品和品牌事实直接支撑白酒消费叙事。"
    assert payload["exclusion_rationale"] == ["不是一般食品饮料泛标签。"]
    assert payload["confidence_components"]["business_relevance"] == 0.95
    assert payload["promotion_effect"] == "none"
    assert payload["recommended_action"] == "human_review"
    assert payload["evidence_items"] == [
        {
            "source_name": "Annual report",
            "source_url": "https://example.test/a",
            "source_type": "annual_report",
            "evidence_date": "2026-04-17",
            "evidence_summary": "Annual report support.",
            "supports": ["business_relevance", "durability"],
            "supported_claim_types": ["business_relevance", "durability"],
        }
    ]


def test_evidence_pack_detail_by_pack_id_matches_stock_narrative_lookup(tmp_path):
    config = _write_seed_files(tmp_path)
    _write_detail_evidence_pack(config)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        packs = _get_json(f"{base_url}/api/v1/narratives/evidence-packs")
        evidence_pack_id = packs["data"]["packs"][0]["proposed_mappings"][0][
            "evidence_pack_id"
        ]
        by_id = _get_json(
            f"{base_url}/api/v1/narratives/evidence-packs/{evidence_pack_id}"
        )
        by_query = _get_json(
            f"{base_url}/api/v1/narratives/evidence-packs/detail"
            "?stock_code=600519&narrative_id=N_BAIJIU"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert by_id["data"] == by_query["data"]


def test_evidence_pack_detail_missing_returns_missing_envelope_without_mutation(tmp_path):
    config = _write_seed_files(tmp_path)
    _write_detail_evidence_pack(config)
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
        response = _get_json(
            f"{base_url}/api/v1/narratives/evidence-packs/detail"
            "?stock_code=600519&narrative_id=N_UNKNOWN"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "missing"
    assert response["data"]["error"]["code"] == "EVIDENCE_PACK_NOT_FOUND"
    assert response["warnings"][0]["code"] == "EVIDENCE_PACK_NOT_FOUND"
    assert not config.review_actions_path.exists()
    assert not config.intake_ledger_path.exists()
    for path, before_text in source_snapshots.items():
        assert path.read_text(encoding="utf-8") == before_text


def test_candidate_detail_returns_review_history_preflight_and_evidence_refs(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "defer",
                "reviewed_by": "test-reviewer",
                "review_note": "Need one more look.",
            },
        )
        latest_action = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Ready for detail preflight.",
            },
        )
        detail = _get_json(f"{base_url}/api/v1/narratives/candidates/C_SEED")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert detail["status"] == "available"
    assert detail["trust_metadata"]["trust_status"] == "candidate_untrusted"
    payload = detail["data"]
    assert payload["version"] == "candidate-narrative-detail-v1"
    assert payload["candidate_narrative_id"] == "C_SEED"
    assert payload["candidate"]["name"] == "机器人执行器"
    assert payload["trust_status"] == "candidate_untrusted"
    assert payload["latest_review_action"]["review_action_id"] == latest_action[
        "data"
    ]["decision"]["review_action_id"]
    assert [item["action"] for item in payload["review_history"]] == [
        "defer",
        "approve",
    ]
    assert payload["promotion_preflight"]["result"] == "ready_for_trust_audit"
    assert payload["missing_gates"] == []
    assert payload["recommended_action"] == "run_trust_audit"
    assert payload["source_evidence_refs"]["representative_citation_ids"] == [
        "SRC_1",
        "SRC_2",
    ]


def test_candidate_detail_unknown_returns_missing_envelope_without_mutation(tmp_path):
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
        response = _get_json(f"{base_url}/api/v1/narratives/candidates/C_UNKNOWN")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "missing"
    assert response["data"]["candidate_narrative_id"] == "C_UNKNOWN"
    assert response["data"]["error"]["code"] == "CANDIDATE_NOT_FOUND"
    assert response["warnings"][0]["code"] == "CANDIDATE_NOT_FOUND"
    assert not config.review_actions_path.exists()
    assert not config.intake_ledger_path.exists()
    for path, before_text in source_snapshots.items():
        assert path.read_text(encoding="utf-8") == before_text


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


def test_intake_review_and_preflight_cannot_create_trusted_records(tmp_path):
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
        intake = _post_json(
            f"{base_url}/api/v1/narratives/intake/events",
            {
                "events": [
                    {
                        "event_id": "EVT_PROMOTION_BOUNDARY",
                        "source_type": "manual",
                        "event_time": "2026-05-28T10:00:00+08:00",
                        "title": "Boundary candidate",
                        "source_url": "manual://promotion-boundary",
                        "candidate_narratives": [
                            {
                                "candidate_narrative_id": "C_BOUNDARY",
                                "name": "Boundary candidate",
                                "canonical_taxonomy": "boundary",
                                "confidence": 0.7,
                            }
                        ],
                    }
                ]
            },
        )
        review = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Approval alone must not promote.",
            },
        )
        preflight = _post_json(
            f"{base_url}/api/v1/narratives/promotion/preflight",
            {"candidate_narrative_id": "C_SEED"},
        )
        candidates = _get_json(f"{base_url}/api/v1/narratives/candidates")
        audit = _get_json(f"{base_url}/api/v1/narratives/trust-audits/latest")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert intake["data"]["candidate_narratives"][0]["trust_status"] == (
        "candidate_untrusted"
    )
    assert review["data"]["decision"]["promotion_effect"] == "none"
    assert preflight["data"]["result"] == "ready_for_trust_audit"
    assert preflight["data"]["promotion_effect"] == "none"
    assert audit["data"]["result"] == "blocked"
    assert {
        item["trust_status"] for item in candidates["data"]["candidate_narratives"]
    } == {"candidate_untrusted"}
    for payload in (intake, review, preflight, candidates, audit):
        assert "trusted_validated" not in json.dumps(payload, ensure_ascii=False)
    for path, before_text in source_snapshots.items():
        assert path.read_text(encoding="utf-8") == before_text
    assert not config.promotion_decisions_path.exists()


def test_promotion_commit_reports_missing_gates_without_writes(tmp_path):
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
        error = _post_json_error(
            f"{base_url}/api/v1/narratives/promotion/commit",
            {
                "candidate_narrative_id": "C_SEED",
                "target_narrative_id": "N_ROBOTICS",
                "review_action_id": "RA_MISSING",
                "trust_audit_id": "TA_MISSING",
                "promoted_by": "test-promoter",
                "promotion_note": "Should fail missing gates.",
                "target_stock_codes": ["600519"],
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert error["status"] == "failed"
    assert error["data"]["error"]["code"] == "PROMOTION_GATES_MISSING"
    assert set(error["data"]["missing_gates"]) == {
        "service_review_approval",
        "trust_audit_pass",
    }
    assert error["data"]["promotion_effect"] == "none"
    for path, before_text in source_snapshots.items():
        assert path.read_text(encoding="utf-8") == before_text
    assert not config.promotion_decisions_path.exists()


def test_promotion_commit_atomically_writes_trusted_records_and_decision(tmp_path):
    config = _write_seed_files(tmp_path)
    _write_detail_evidence_pack(config)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        approval = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "test-reviewer",
                "review_note": "Ready for trusted promotion.",
            },
        )
        preflight = _post_json(
            f"{base_url}/api/v1/narratives/promotion/preflight",
            {"candidate_narrative_id": "C_SEED"},
        )
        response = _post_json(
            f"{base_url}/api/v1/narratives/promotion/commit",
            {
                "candidate_narrative_id": "C_SEED",
                "target_narrative_id": "N_ROBOTICS_TRUSTED",
                "review_action_id": approval["data"]["decision"]["review_action_id"],
                "trust_audit_id": "TA_PASS_ROBOTICS",
                "trust_audit_result": "passed",
                "promoted_by": "test-promoter",
                "promotion_note": "All explicit gates passed.",
                "target_stock_codes": ["600519"],
                "source_metadata": {"source": "promotion-workflow-test"},
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    registry = json.loads(config.registry_path.read_text(encoding="utf-8"))
    mappings = json.loads(config.mappings_path.read_text(encoding="utf-8"))
    evidence = json.loads(config.evidence_packs_path.read_text(encoding="utf-8"))
    decisions = json.loads(config.promotion_decisions_path.read_text(encoding="utf-8"))
    decision = response["data"]["decision"]

    assert preflight["data"]["result"] == "ready_for_trust_audit"
    assert response["status"] == "available"
    assert response["trust_metadata"]["trust_status"] == "trusted_validated"
    assert decision["promotion_decision_id"].startswith("PD_")
    assert decision["ledger_record_type"] == "promotion_decision"
    assert decision["candidate_narrative_id"] == "C_SEED"
    assert decision["target_narrative_id"] == "N_ROBOTICS_TRUSTED"
    assert decision["trust_status_before"] == "candidate_untrusted"
    assert decision["trust_status_after"] == "trusted_validated"
    assert decision["promotion_effect"] == "trusted_validated"
    assert decision["atomic_write_set"] == [
        "trusted_registry_record",
        "trusted_stock_mapping_record",
        "trusted_evidence_pack_record",
        "promotion_decision_ledger_record",
    ]
    trusted_narrative = next(
        item
        for item in registry["narratives"]
        if item["narrative_id"] == "N_ROBOTICS_TRUSTED"
    )
    trusted_mapping = next(
        item
        for item in mappings["mappings"]
        if item["narrative_id"] == "N_ROBOTICS_TRUSTED"
    )
    trusted_pack = next(pack for pack in evidence["packs"] if pack["stock_code"] == "600519")
    evidence_mappings = {
        item["narrative_id"]: item for item in trusted_pack["proposed_mappings"]
    }
    assert trusted_narrative["trust_status"] == "trusted_validated"
    assert trusted_mapping["trust_status"] == "trusted_validated"
    assert trusted_mapping["source_trust_status"] == "trusted_validated"
    assert set(evidence_mappings) == {"N_BAIJIU", "N_ROBOTICS_TRUSTED"}
    assert evidence_mappings["N_ROBOTICS_TRUSTED"]["trust_status"] == (
        "trusted_validated"
    )
    assert decisions["version"] == "narrative-promotion-decisions-v1"
    assert decisions["items"] == [decision]


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


def test_radar_contract_declares_service_ownership_score_schema_and_metadata(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/radar/contract")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    assert response["source"] == "narrative_service"
    payload = response["data"]
    assert payload["version"] == "narrative-radar-contract-v1"
    assert payload["ownership"] == {
        "radar_owner": "narrative_service",
        "provider_owner": "gateway",
        "consumer_role": "fni_consumes_service_api_only",
        "score_authority": "narrative_service",
    }
    assert payload["service_owned_endpoints"] == [
        "/api/v1/narratives/radar/contract",
        "/api/v1/narratives/radar/signals",
        "/api/v1/narratives/radar/scores",
        "/api/v1/narratives/radar/mined-candidates",
        "/api/v1/narratives/radar/bubbles",
        "/api/v1/narratives/radar/evidence",
        "/api/v1/narratives/radar/preview",
        "/api/v1/narratives/radar/ui-contract",
        "/narratives/radar",
    ]
    assert payload["response_envelope"] == {
        "status": "available|degraded|missing|failed",
        "source": "narrative_service",
        "provider": "stock-narrative-service",
        "provider_version": "v0",
        "data": "endpoint payload",
        "warnings": "degraded or missing source metadata",
        "diagnostics": "operational diagnostics",
        "trust_metadata": "candidate/trusted state metadata",
    }
    score_schema = payload["score_schema"]
    assert score_schema["formula_version"] == "radar-deterministic-v0"
    assert score_schema["required_fields"] == [
        "heat_score",
        "trend_score",
        "momentum_state",
        "market_confirmation_score",
        "evidence_quality_score",
        "source_attention_components",
        "window_start",
        "window_end",
        "baseline_window",
        "formula_version",
        "degradation_warnings",
    ]
    assert score_schema["ai_policy"] == (
        "AI summaries may explain evidence later but cannot override deterministic scores."
    )
    assert payload["degraded_metadata_fields"] == [
        "degradation_warnings",
        "source_availability",
        "missing_source_types",
        "formula_version",
    ]


def test_radar_signals_replay_fixture_events_into_time_series_snapshots(tmp_path):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    {
                        "event_id": "EVT_ROBOT_1",
                        "source_type": "news",
                        "event_time": "2026-05-28T09:15:00+08:00",
                        "ingested_at": "2026-05-28T09:16:00+08:00",
                        "title": "机器人执行器订单增加",
                        "source_url": "gateway://news/robot-1",
                        "stock_codes": ["300124"],
                        "extracted_entities": {
                            "tickers": ["300124"],
                            "sectors": ["机器人"],
                            "concepts": ["执行器"],
                            "keywords": ["订单", "执行器"],
                        },
                        "source_metadata": {
                            "provider": "gateway_news_briefs",
                            "permission_status": "licensed",
                            "degradation_state": "available",
                        },
                        "candidate_narratives": [
                            {
                                "candidate_narrative_id": "C_ROBOT",
                                "name": "机器人执行器",
                                "confidence": 0.7,
                                "representative_citation_ids": ["SRC_ROBOT_1"],
                            }
                        ],
                    },
                    {
                        "event_id": "EVT_ROBOT_2",
                        "source_type": "announcement",
                        "event_time": "2026-05-28T15:30:00+08:00",
                        "title": "机器人供应链公告",
                        "source_url": "gateway://announcements/robot-2",
                        "stock_codes": ["002472"],
                        "source_weight": 1.2,
                        "candidate_narratives": [
                            {
                                "candidate_narrative_id": "C_ROBOT",
                                "name": "机器人执行器",
                                "confidence": 0.8,
                                "representative_citation_ids": ["SRC_ROBOT_2"],
                            }
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/radar/signals")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    payload = response["data"]
    assert payload["version"] == "narrative-radar-source-signals-v1"
    assert payload["source_model"]["storage_model"] == "append_only_source_signal_ledger"
    assert payload["source_model"]["window_granularities"] == ["hourly", "daily"]
    assert payload["degradation_warnings"] == []
    assert [signal["source_event_id"] for signal in payload["signals"]] == [
        "EVT_ROBOT_1",
        "EVT_ROBOT_2",
    ]
    assert payload["signals"][0] == {
        "signal_id": payload["signals"][0]["signal_id"],
        "source_event_id": "EVT_ROBOT_1",
        "source_type": "news",
        "candidate_narrative_id": "C_ROBOT",
        "narrative_name": "机器人执行器",
        "extracted_entities": {
            "tickers": ["300124"],
            "sectors": ["机器人"],
            "concepts": ["执行器"],
            "keywords": ["订单", "执行器"],
        },
        "event_time": "2026-05-28T09:15:00+08:00",
        "ingested_at": "2026-05-28T09:16:00+08:00",
        "signal_strength": 0.7,
        "source_weight": 1.0,
        "weighted_attention": 0.7,
        "evidence_refs": ["SRC_ROBOT_1"],
        "source_metadata": {
            "provider": "gateway_news_briefs",
            "permission_status": "licensed",
            "degradation_state": "available",
        },
        "trust_status": "candidate_untrusted",
    }
    assert payload["window_snapshots"] == [
        {
            "window_id": "daily:2026-05-28:C_ROBOT",
            "granularity": "daily",
            "window_start": "2026-05-28T00:00:00+08:00",
            "window_end": "2026-05-29T00:00:00+08:00",
            "candidate_narrative_id": "C_ROBOT",
            "narrative_name": "机器人执行器",
            "source_signal_count": 2,
            "source_count": 2,
            "total_signal_strength": 1.5,
            "weighted_attention": 1.66,
            "source_event_ids": ["EVT_ROBOT_1", "EVT_ROBOT_2"],
            "source_types": ["announcement", "news"],
            "degradation_warnings": [],
        }
    ]
    assert not config.intake_ledger_path.exists()


def test_radar_scores_are_deterministic_and_mark_sustained_heating(tmp_path):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    _radar_event("EVT_ROBOT_D1", "2026-05-26T10:00:00+08:00", 0.3),
                    _radar_event("EVT_ROBOT_D2", "2026-05-27T10:00:00+08:00", 0.5),
                    _radar_event("EVT_ROBOT_D3A", "2026-05-28T10:00:00+08:00", 0.8),
                    _radar_event(
                        "EVT_ROBOT_D3B",
                        "2026-05-28T15:30:00+08:00",
                        0.7,
                        source_type="announcement",
                        source_weight=1.2,
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    config.market_confirmation_path.parent.mkdir(parents=True, exist_ok=True)
    config.market_confirmation_path.write_text(
        json.dumps(
            {
                "version": "radar-market-confirmation-v1",
                "items": [
                    {
                        "candidate_narrative_id": "C_ROBOT",
                        "market_confirmation_score": 64,
                        "status": "available",
                        "source": "gateway_contract_fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(
            f"{base_url}/api/v1/narratives/radar/scores"
            "?as_of=2026-05-29T00:00:00+08:00"
            "&window_days=1&baseline_days=3&half_life_hours=24"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    payload = response["data"]
    assert payload["version"] == "narrative-radar-scores-v1"
    assert payload["scoring_config"] == {
        "as_of": "2026-05-29T00:00:00+08:00",
        "window_days": 1,
        "baseline_days": 3,
        "recency_decay_half_life_hours": 24.0,
        "formula_version": "radar-deterministic-v0",
    }
    assert payload["market_confirmation_adapter"] == {
        "adapter": "local_contract_fixture",
        "source_owner": "gateway",
        "direct_provider_access": False,
        "path": str(config.market_confirmation_path),
    }
    score = payload["scores"][0]
    assert score["candidate_narrative_id"] == "C_ROBOT"
    assert score["narrative_name"] == "机器人执行器"
    assert score["heat_score"] == 82.0
    assert score["trend_score"] == 79.55
    assert score["trend_acceleration"] == 27.8
    assert score["momentum_state"] == "heating"
    assert score["market_confirmation_score"] == 64.0
    assert score["evidence_quality_score"] == 100.0
    assert score["formula_version"] == "radar-deterministic-v0"
    assert score["window_start"] == "2026-05-28T00:00:00+08:00"
    assert score["window_end"] == "2026-05-29T00:00:00+08:00"
    assert score["baseline_window"] == {
        "window_start": "2026-05-26T00:00:00+08:00",
        "window_end": "2026-05-28T00:00:00+08:00",
        "average_weighted_attention": 0.16,
    }
    assert score["source_attention_components"] == {
        "current_weighted_attention": 1.64,
        "baseline_weighted_attention": 0.33,
        "baseline_daily_average": 0.16,
        "previous_window_weighted_attention": 0.25,
        "source_signal_count": 4,
        "current_source_signal_count": 2,
    }
    assert score["degradation_warnings"] == []
    assert "AI" not in json.dumps(score, ensure_ascii=False)


def test_radar_scores_degrade_market_confirmation_without_suppressing_source_heat(
    tmp_path,
):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    _radar_event("EVT_ROBOT_CURRENT", "2026-05-28T10:00:00+08:00", 0.9)
                ],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(
            f"{base_url}/api/v1/narratives/radar/scores"
            "?as_of=2026-05-29T00:00:00+08:00"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    score = response["data"]["scores"][0]
    assert response["status"] == "available"
    assert score["heat_score"] > 0
    assert score["market_confirmation_score"] == 0.0
    assert score["degradation_warnings"] == [
        {
            "code": "MARKET_CONFIRMATION_MISSING",
            "message": "No normalized market confirmation is available for C_ROBOT.",
            "classification": "source_degraded",
        }
    ]
    assert response["data"]["degradation_warnings"] == score["degradation_warnings"]
    assert response["data"]["market_confirmation_adapter"]["direct_provider_access"] is False
    assert not config.intake_ledger_path.exists()


def test_radar_mining_creates_candidate_signals_from_structured_events(tmp_path):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    _structured_radar_source_event(
                        "EVT_NEWS_ROBOT",
                        "news",
                        "gateway://news/robot",
                        ["300124"],
                    ),
                    _structured_radar_source_event(
                        "EVT_ANN_ROBOT",
                        "announcement",
                        "gateway://announcements/robot",
                        ["002472"],
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        mined = _get_json(f"{base_url}/api/v1/narratives/radar/mined-candidates")
        signals = _get_json(f"{base_url}/api/v1/narratives/radar/signals")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert mined["status"] == "available"
    payload = mined["data"]
    assert payload["version"] == "narrative-radar-mined-candidates-v1"
    assert payload["mining_policy"] == {
        "method": "structured_event_cooccurrence_v0",
        "allowed_source_types": ["announcement", "manual", "news"],
        "excluded_source_types": ["social_future"],
        "browser_automation": False,
        "market_confirmation_used_as_source": False,
        "trust_promotion_effect": "none",
    }
    candidate = payload["candidate_narratives"][0]
    assert candidate["candidate_narrative_id"].startswith("C_MINED_")
    assert candidate["name"] == "机器人执行器"
    assert candidate["trust_status"] == "candidate_untrusted"
    assert candidate["human_review_status"] == "candidate"
    assert candidate["source_types"] == ["announcement", "news"]
    assert candidate["stock_codes"] == ["002472", "300124"]
    assert candidate["extracted_entities"] == {
        "tickers": ["002472", "300124"],
        "sectors": ["机器人"],
        "concepts": ["执行器"],
        "keywords": ["执行器", "订单"],
    }
    assert [item["source_event_id"] for item in candidate["evidence_refs"]] == [
        "EVT_ANN_ROBOT",
        "EVT_NEWS_ROBOT",
    ]
    assert {signal["candidate_narrative_id"] for signal in signals["data"]["signals"]} == {
        candidate["candidate_narrative_id"]
    }
    assert [signal["source_event_id"] for signal in signals["data"]["signals"]] == [
        "EVT_ANN_ROBOT",
        "EVT_NEWS_ROBOT",
    ]
    assert {signal["trust_status"] for signal in signals["data"]["signals"]} == {
        "candidate_untrusted"
    }
    assert not config.intake_ledger_path.exists()


def test_radar_mining_excludes_reserved_social_sources_and_discloses_policy(tmp_path):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    _structured_radar_source_event(
                        "EVT_SOCIAL_RESERVED",
                        "social_future",
                        "social-future://reserved",
                        ["300124"],
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        mined = _get_json(f"{base_url}/api/v1/narratives/radar/mined-candidates")
        signals = _get_json(f"{base_url}/api/v1/narratives/radar/signals")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert mined["data"]["candidate_narratives"] == []
    assert mined["data"]["excluded_event_count"] == 1
    assert mined["data"]["mining_policy"]["excluded_source_types"] == ["social_future"]
    assert mined["data"]["mining_policy"]["browser_automation"] is False
    assert mined["data"]["mining_policy"]["market_confirmation_used_as_source"] is False
    assert signals["data"]["signals"] == []


def test_radar_bubbles_return_visualization_ready_contract_without_recalculation(
    tmp_path,
):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    _radar_event("EVT_ROBOT_D1", "2026-05-26T10:00:00+08:00", 0.3),
                    _radar_event("EVT_ROBOT_D2", "2026-05-27T10:00:00+08:00", 0.5),
                    _radar_event("EVT_ROBOT_D3A", "2026-05-28T10:00:00+08:00", 0.8),
                    _radar_event(
                        "EVT_ROBOT_D3B",
                        "2026-05-28T15:30:00+08:00",
                        0.7,
                        source_type="announcement",
                        source_weight=1.2,
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )
    config.market_confirmation_path.parent.mkdir(parents=True, exist_ok=True)
    config.market_confirmation_path.write_text(
        json.dumps(
            {
                "version": "radar-market-confirmation-v1",
                "items": [
                    {
                        "candidate_narrative_id": "C_ROBOT",
                        "market_confirmation_score": 64,
                        "status": "available",
                        "source": "gateway_contract_fixture",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(
            f"{base_url}/api/v1/narratives/radar/bubbles"
            "?as_of=2026-05-29T00:00:00+08:00"
            "&window_days=1&baseline_days=3&half_life_hours=24"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    payload = response["data"]
    assert payload["version"] == "narrative-radar-bubbles-v1"
    assert payload["visualization_contract"] == {
        "version": "bubble-chart-contract-v1",
        "library_agnostic": True,
        "dimensions": {
            "size": "heat_score",
            "x": "trend_acceleration",
            "y": "market_confirmation_score",
            "color": "momentum_state",
            "border": "trust_status",
            "marker": "evidence_quality_score",
            "tooltip": [
                "evidence_refs",
                "representative_stocks",
                "source_count",
                "score_components",
                "sparkline_points",
                "degradation_warnings",
            ],
        },
    }
    bubble = payload["bubbles"][0]
    assert set(bubble) >= {
        "narrative_id",
        "narrative_name",
        "heat_score",
        "trend_score",
        "trend_acceleration",
        "momentum_state",
        "market_confirmation_score",
        "trust_status",
        "evidence_quality_score",
        "source_count",
        "representative_stocks",
        "window_metrics",
        "sparkline_points",
        "evidence_refs",
        "score_components",
        "degradation_warnings",
        "updated_at",
        "visual_encoding",
    }
    assert bubble["narrative_id"] == "C_ROBOT"
    assert bubble["detail_path"] == (
        "/api/v1/narratives/radar/evidence?narrative_id=C_ROBOT"
    )
    assert bubble["narrative_name"] == "机器人执行器"
    assert bubble["heat_score"] == 82.0
    assert bubble["trend_score"] == 79.55
    assert bubble["trend_acceleration"] == 27.8
    assert bubble["momentum_state"] == "heating"
    assert bubble["market_confirmation_score"] == 64.0
    assert bubble["trust_status"] == "candidate_untrusted"
    assert bubble["source_count"] == 4
    assert bubble["representative_stocks"] == ["300124"]
    assert bubble["window_metrics"] == {
        "window_start": "2026-05-28T00:00:00+08:00",
        "window_end": "2026-05-29T00:00:00+08:00",
        "baseline_window": {
            "window_start": "2026-05-26T00:00:00+08:00",
            "window_end": "2026-05-28T00:00:00+08:00",
            "average_weighted_attention": 0.16,
        },
    }
    assert bubble["sparkline_points"] == [
        {"window_start": "2026-05-26T00:00:00+08:00", "weighted_attention": 0.3},
        {"window_start": "2026-05-27T00:00:00+08:00", "weighted_attention": 0.5},
        {"window_start": "2026-05-28T00:00:00+08:00", "weighted_attention": 1.64},
    ]
    assert bubble["evidence_refs"] == [
        "SRC_EVT_ROBOT_D1",
        "SRC_EVT_ROBOT_D2",
        "SRC_EVT_ROBOT_D3A",
        "SRC_EVT_ROBOT_D3B",
    ]
    assert bubble["score_components"] == bubble["source_attention_components"]
    assert bubble["visual_encoding"] == {
        "size": 82.0,
        "x": 27.8,
        "y": 64.0,
        "color": "heating",
        "border": "candidate_untrusted",
        "marker": 100.0,
    }
    assert payload["degradation_warnings"] == []


def test_radar_bubbles_empty_inputs_return_structured_metadata(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/radar/bubbles")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    assert response["data"]["bubbles"] == []
    assert response["data"]["degradation_warnings"] == [
        {
            "code": "RADAR_BUBBLES_EMPTY",
            "message": "No radar bubbles are available from current source signals.",
            "classification": "product_data_gap",
        }
    ]
    assert response["data"]["visualization_contract"]["library_agnostic"] is True


def test_radar_evidence_detail_tracks_review_state_transitions(tmp_path):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [_seed_candidate_radar_event()],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        pending = _get_json(
            f"{base_url}/api/v1/narratives/radar/evidence?narrative_id=C_SEED"
            "&as_of=2026-05-29T00:00:00+08:00"
        )
        approval = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "radar-reviewer",
                "review_note": "Structured radar detail is reviewable.",
            },
        )
        reviewed = _get_json(
            f"{base_url}/api/v1/narratives/radar/evidence?narrative_id=C_SEED"
            "&as_of=2026-05-29T00:00:00+08:00"
        )
        rejection = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "reject",
                "reviewed_by": "radar-reviewer",
                "review_note": "Not durable enough for current radar.",
            },
        )
        rejected = _get_json(
            f"{base_url}/api/v1/narratives/radar/evidence?narrative_id=C_SEED"
            "&as_of=2026-05-29T00:00:00+08:00"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert pending["status"] == "available"
    assert pending["data"]["version"] == "narrative-radar-evidence-detail-v1"
    assert pending["data"]["narrative_id"] == "C_SEED"
    assert pending["data"]["linked_record"] == {
        "record_type": "candidate_narrative",
        "candidate_narrative_id": "C_SEED",
        "trust_status": "candidate_untrusted",
    }
    assert pending["data"]["radar_state"]["state"] == "candidate"
    assert pending["data"]["review_state"]["status"] == "pending_review"
    assert reviewed["data"]["radar_state"]["state"] == "reviewed"
    assert reviewed["data"]["review_state"]["latest_review_action_id"] == approval[
        "data"
    ]["decision"]["review_action_id"]
    assert reviewed["data"]["review_state"]["status"] == "ready_for_trust_audit"
    assert rejected["data"]["radar_state"]["state"] == "rejected"
    assert rejected["data"]["review_state"]["latest_review_action_id"] == rejection[
        "data"
    ]["decision"]["review_action_id"]
    assert rejected["data"]["review_state"]["status"] == "rejected"
    assert rejected["data"]["trust_status"] == "candidate_untrusted"
    assert rejected["data"]["promotion_effect"] == "none"
    assert rejected["data"]["representative_stocks"] == ["300124"]
    assert rejected["data"]["extracted_entities"] == {
        "tickers": ["300124"],
        "sectors": ["机器人"],
        "concepts": ["执行器"],
        "keywords": ["执行器", "订单"],
    }
    assert rejected["data"]["evidence_refs"] == [
        {
            "source_event_id": "EVT_SEED_RADAR",
            "source_type": "news",
            "source_url": "gateway://news/seed-radar",
            "title": "机器人执行器 seed radar source",
            "event_time": "2026-05-28T10:00:00+08:00",
            "evidence_refs": ["SRC_SEED_RADAR"],
        }
    ]
    assert set(rejected["data"]["score_components"]) >= {
        "current_weighted_attention",
        "baseline_weighted_attention",
        "baseline_daily_average",
        "previous_window_weighted_attention",
    }
    assert rejected["data"]["historical_interpretation"] == (
        "Radar detail remains readable after review state changes; rejected or "
        "deprecated narratives are not current trusted signals."
    )


def test_radar_preview_surface_uses_bubble_api_contract_without_report_semantics(
    tmp_path,
):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [_radar_event("EVT_ROBOT_D3A", "2026-05-28T10:00:00+08:00", 0.8)],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        preview = _get_json(
            f"{base_url}/api/v1/narratives/radar/preview"
            "?as_of=2026-05-29T00:00:00+08:00"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert preview["status"] == "available"
    payload = preview["data"]
    assert payload["version"] == "narrative-radar-preview-v1"
    assert payload["surface"] == {
        "type": "service_dev_preview",
        "not_report_product": True,
        "score_recalculation": "none",
        "data_source_endpoint": "/api/v1/narratives/radar/bubbles",
    }
    assert payload["layout_contract"] == {
        "responsive": True,
        "min_width": 320,
        "preferred_width": 960,
        "bubble_layer": "svg_or_canvas_client_choice",
    }
    assert payload["visualization_contract"]["dimensions"]["size"] == "heat_score"
    assert payload["render_model"]["bubbles"][0]["narrative_id"] == "C_ROBOT"
    assert payload["render_model"]["legend"] == {
        "size": "heat",
        "color": "momentum_state",
        "border": "trust_status",
        "x_axis": "trend_acceleration",
        "y_axis": "market_confirmation_score",
    }
    assert "report" not in json.dumps(payload["render_model"], ensure_ascii=False).lower()


def test_radar_ui_contract_declares_frontend_boundary_and_states(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/radar/ui-contract")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response["status"] == "available"
    payload = response["data"]
    assert payload["version"] == "narrative-radar-ui-contract-v1"
    assert payload["frontend_boundary"] == {
        "score_authority": "narrative_service_api",
        "ui_responsibility": ["rendering", "filters", "interactions", "drill_down_navigation"],
        "score_recalculation": "forbidden",
        "fni_report_role": "may_link_later_must_not_calculate_radar",
    }
    assert payload["data_endpoints"] == {
        "list": "/api/v1/narratives/radar/bubbles",
        "detail": "/api/v1/narratives/radar/evidence?narrative_id=<id>",
        "preview_payload": "/api/v1/narratives/radar/preview",
    }
    assert payload["stable_identifiers"] == [
        "narrative_id",
        "candidate_narrative_id",
        "evidence_refs",
        "review_state.status",
        "trust_status",
    ]
    assert payload["frontend_states"] == ["loading", "ready", "empty", "degraded", "stale"]
    assert payload["visual_mapping"]["version"] == "bubble-chart-contract-v1"
    assert payload["visual_mapping"]["dimensions"]["size"] == "heat_score"
    assert "formula" not in json.dumps(payload, ensure_ascii=False).lower()


def test_radar_service_ui_renders_bubble_surface_without_score_recalculation(tmp_path):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [_radar_event("EVT_ROBOT_D3A", "2026-05-28T10:00:00+08:00", 0.8)],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        html = _get_text(
            f"{base_url}/narratives/radar?as_of=2026-05-29T00:00:00+08:00"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert "Narrative Radar" in html
    assert "机器人执行器" in html
    assert 'data-score-source="narrative-service"' in html
    assert "score recalculation: none" in html
    assert "candidate_untrusted" in html
    assert "/api/v1/narratives/radar/evidence?narrative_id=C_ROBOT" in html
    assert "heat_score" in html
    assert "market_confirmation_score" in html
    assert "fund report" not in html.lower()


def test_radar_service_ui_renders_empty_diagnostics(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        html = _get_text(f"{base_url}/narratives/radar")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert "Narrative Radar" in html
    assert "No radar bubbles are available" in html
    assert "RADAR_BUBBLES_EMPTY" in html
    assert 'data-ui-state="empty"' in html


def test_radar_evidence_optional_explanation_is_disabled_by_default_and_non_authoritative(
    tmp_path,
):
    config = _write_seed_files(tmp_path)
    config.candidate_events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [_seed_candidate_radar_event()],
            }
        ),
        encoding="utf-8",
    )
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        disabled = _get_json(
            f"{base_url}/api/v1/narratives/radar/evidence?narrative_id=C_SEED"
        )
        enabled = _get_json(
            f"{base_url}/api/v1/narratives/radar/evidence?narrative_id=C_SEED"
            "&include_explanation=true"
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert disabled["data"]["explanation"] == {
        "enabled": False,
        "authoritative": False,
        "score_effect": "none",
        "trust_effect": "none",
    }
    explanation = enabled["data"]["explanation"]
    assert explanation["enabled"] is True
    assert explanation["authoritative"] is False
    assert explanation["score_effect"] == "none"
    assert explanation["trust_effect"] == "none"
    assert explanation["generator"] == "optional_ai_summary_contract_v0"
    assert explanation["summary"].startswith("机器人执行器 is explained from 1 source")
    assert explanation["evidence_refs"] == ["EVT_SEED_RADAR"]
    assert enabled["data"]["score_components"] == disabled["data"]["score_components"]
    assert enabled["data"]["trust_status"] == disabled["data"]["trust_status"]


def test_review_workflow_contract_defines_state_machine_and_guardrails(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/review-workflow/contract")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    payload = response["data"]
    assert payload["version"] == "narrative-review-workflow-contract-v1"
    assert payload["states"] == [
        "candidate_untrusted",
        "pending_review",
        "approved_blocked_by_evidence",
        "ready_for_trust_audit",
        "trusted_validated",
        "rejected",
        "deferred",
        "deprecated",
    ]
    assert payload["rules"] == {
        "intake": "creates candidate_untrusted records only",
        "review_action": "approve/reject/defer only; cannot promote directly",
        "preflight": "non_mutating",
        "promotion_commit": "only trusted-record write path",
        "failed_promotion": "writes no trusted records",
    }
    assert payload["transitions"]["pending_review"]["approve"] == [
        "approved_blocked_by_evidence",
        "ready_for_trust_audit",
    ]
    assert payload["audit_fields"] == [
        "reviewed_by",
        "action",
        "reviewed_at",
        "review_note",
        "promotion_decision_id",
    ]


def test_review_workflow_summary_tracks_happy_path_to_trusted_promotion(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        before = _get_json(f"{base_url}/api/v1/narratives/review-workflow")
        review = _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "approve",
                "reviewed_by": "workflow-reviewer",
                "review_note": "Evidence, rationale, and exclusion gates are present.",
            },
        )
        preflight = _post_json(
            f"{base_url}/api/v1/narratives/promotion/preflight",
            {"candidate_narrative_id": "C_SEED"},
        )
        commit = _post_json(
            f"{base_url}/api/v1/narratives/promotion/commit",
            {
                "candidate_narrative_id": "C_SEED",
                "target_narrative_id": "N_ROBOTICS_ACTUATOR",
                "target_stock_codes": ["300124"],
                "review_action_id": review["data"]["decision"]["review_action_id"],
                "trust_audit_id": "TA_WORKFLOW",
                "trust_audit_result": "passed",
                "promoted_by": "workflow-reviewer",
                "promotion_note": "Controlled fixture promotion.",
            },
        )
        after = _get_json(f"{base_url}/api/v1/narratives/review-workflow")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert before["data"]["items"][0]["workflow_state"] == "pending_review"
    assert preflight["data"]["result"] == "ready_for_trust_audit"
    assert commit["data"]["decision"]["promotion_effect"] == "trusted_validated"
    item = after["data"]["items"][0]
    assert item["workflow_state"] == "trusted_validated"
    assert item["promotion_decision_id"] == commit["data"]["decision"]["promotion_decision_id"]
    assert item["audit_trail"]["latest_review_action_id"] == review["data"]["decision"][
        "review_action_id"
    ]
    assert item["audit_trail"]["promotion_decision_id"] == commit["data"]["decision"][
        "promotion_decision_id"
    ]
    assert after["data"]["summary"]["trusted_validated"] == 1


def test_review_workflow_html_exposes_blocked_and_deferred_paths(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        _post_json(
            f"{base_url}/api/v1/narratives/review-actions",
            {
                "candidate_narrative_id": "C_SEED",
                "action": "defer",
                "reviewed_by": "workflow-reviewer",
                "review_note": "Needs another source cycle.",
            },
        )
        html = _get_text(f"{base_url}/narratives/review")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert "Narrative Review Workflow" in html
    assert "C_SEED" in html
    assert "deferred" in html
    assert "promotion preflight" in html
    assert "promotion commit is the only trusted-record write path" in html


def test_job_schedule_contract_declares_definitions_run_ledger_and_bounds(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = _get_json(f"{base_url}/api/v1/narratives/jobs/contract")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    payload = response["data"]
    assert payload["version"] == "narrative-scheduling-contract-v1"
    assert payload["job_definition_fields"] == [
        "job_id",
        "job_type",
        "enabled",
        "schedule",
        "parameters",
        "owner_service",
        "timeout_seconds",
        "concurrency_guard",
        "retry_policy",
        "idempotency_key",
    ]
    assert payload["run_ledger_fields"] == [
        "run_id",
        "job_id",
        "triggered_by",
        "started_at",
        "finished_at",
        "status",
        "duration_ms",
        "warnings",
        "artifacts",
        "error_category",
        "idempotency_key",
    ]
    assert payload["statuses"] == ["queued", "running", "success", "degraded", "failed"]
    assert payload["write_safety"] == {
        "source_intake": "dry_run_by_default",
        "radar_scoring": "read_only_snapshot",
        "live_provider_smoke": "diagnostic_only",
        "report_pack_generation": "artifact_only",
        "trusted_store_mutation": "forbidden",
    }


def test_manual_job_run_appends_idempotent_run_ledger_record(tmp_path):
    config = _write_seed_files(tmp_path)
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        definitions = _get_json(f"{base_url}/api/v1/narratives/jobs/definitions")
        first = _post_json(
            f"{base_url}/api/v1/narratives/jobs/run",
            {
                "job_id": "narrative-radar-scoring",
                "triggered_by": "manual",
                "idempotency_key": "radar-score-manual-1",
            },
        )
        second = _post_json(
            f"{base_url}/api/v1/narratives/jobs/run",
            {
                "job_id": "narrative-radar-scoring",
                "triggered_by": "manual",
                "idempotency_key": "radar-score-manual-1",
            },
        )
        runs = _get_json(f"{base_url}/api/v1/narratives/jobs/runs")
    finally:
        server.shutdown()
        thread.join(timeout=2)

    job_ids = {item["job_id"] for item in definitions["data"]["jobs"]}
    assert job_ids == {
        "live-provider-smoke",
        "source-intake",
        "narrative-radar-scoring",
        "report-pack-generation",
    }
    run = first["data"]["run"]
    assert run["run_id"].startswith("JR_")
    assert run["job_id"] == "narrative-radar-scoring"
    assert run["triggered_by"] == "manual"
    assert run["status"] in {"success", "degraded"}
    assert run["duration_ms"] >= 0
    assert run["started_at"] <= run["finished_at"]
    assert run["error_category"] == ""
    assert run["artifacts"][0]["path"] == "/api/v1/narratives/radar/preview"
    assert second["data"]["run"]["run_id"] == run["run_id"]
    assert second["data"]["run"]["idempotent_replay"] is True
    assert runs["data"]["items"] == [run]
    assert json.loads(config.job_runs_path.read_text(encoding="utf-8"))["items"] == [
        run
    ]


def test_disabled_and_failed_jobs_do_not_mutate_trusted_stores(tmp_path):
    config = _write_seed_files(tmp_path)
    config.job_definitions_path.parent.mkdir(parents=True, exist_ok=True)
    config.job_definitions_path.write_text(
        json.dumps(
            {
                "version": "narrative-job-definitions-v1",
                "jobs": [
                    {
                        "job_id": "disabled-intake",
                        "job_type": "source_intake",
                        "enabled": False,
                        "schedule": {"mode": "manual"},
                        "parameters": {},
                        "owner_service": "stock-narrative-service",
                    },
                    {
                        "job_id": "bad-job",
                        "job_type": "unsupported",
                        "enabled": True,
                        "schedule": {"mode": "manual"},
                        "parameters": {},
                        "owner_service": "stock-narrative-service",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    before_registry = config.registry_path.read_text(encoding="utf-8")
    before_mappings = config.mappings_path.read_text(encoding="utf-8")
    before_evidence = config.evidence_packs_path.read_text(encoding="utf-8")
    server = create_server(("127.0.0.1", 0), config=config)
    thread = _start(server)
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        disabled = _post_json_error(
            f"{base_url}/api/v1/narratives/jobs/run",
            {"job_id": "disabled-intake", "triggered_by": "manual"},
        )
        failed = _post_json(
            f"{base_url}/api/v1/narratives/jobs/run",
            {"job_id": "bad-job", "triggered_by": "manual"},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert disabled["data"]["error"]["code"] == "INVALID_JOB_RUN"
    run = failed["data"]["run"]
    assert run["status"] == "failed"
    assert run["error_category"] == "unsupported_job_type"
    assert run["warnings"][0]["code"] == "JOB_TYPE_UNSUPPORTED"
    assert config.registry_path.read_text(encoding="utf-8") == before_registry
    assert config.mappings_path.read_text(encoding="utf-8") == before_mappings
    assert config.evidence_packs_path.read_text(encoding="utf-8") == before_evidence


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
    promotion_decisions_path = tmp_path / "runtime" / "promotion_decisions.json"
    market_confirmation_path = tmp_path / "runtime" / "radar_market_confirmation.json"
    job_definitions_path = tmp_path / "runtime" / "job_definitions.json"
    job_runs_path = tmp_path / "runtime" / "job_runs.json"
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
        promotion_decisions_path=promotion_decisions_path,
        market_confirmation_path=market_confirmation_path,
        job_definitions_path=job_definitions_path,
        job_runs_path=job_runs_path,
    )


def _write_detail_evidence_pack(config: ServiceConfig) -> None:
    config.evidence_packs_path.write_text(
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
                                "mapping_rationale": "主营产品和品牌事实直接支撑白酒消费叙事。",
                                "exclusion_rationale": ["不是一般食品饮料泛标签。"],
                                "confidence_components": {
                                    "business_relevance": 0.95,
                                    "evidence_quality": 0.8,
                                },
                                "evidence_items": [
                                    {
                                        "source_name": "Annual report",
                                        "source_url": "https://example.test/a",
                                        "source_type": "annual_report",
                                        "evidence_date": "2026-04-17",
                                        "evidence_summary": "Annual report support.",
                                        "supports": [
                                            "business_relevance",
                                            "durability",
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _radar_event(
    event_id: str,
    event_time: str,
    confidence: float,
    *,
    source_type: str = "news",
    source_weight: float | None = None,
) -> dict:
    event = {
        "event_id": event_id,
        "source_type": source_type,
        "event_time": event_time,
        "ingested_at": event_time,
        "title": f"机器人执行器 signal {event_id}",
        "source_url": f"gateway://radar/{event_id}",
        "stock_codes": ["300124"],
        "extracted_entities": {
            "tickers": ["300124"],
            "sectors": ["机器人"],
            "concepts": ["执行器"],
            "keywords": ["订单", "执行器"],
        },
        "source_metadata": {
            "provider": "gateway_news_briefs",
            "permission_status": "licensed",
            "degradation_state": "available",
        },
        "candidate_narratives": [
            {
                "candidate_narrative_id": "C_ROBOT",
                "name": "机器人执行器",
                "confidence": confidence,
                "representative_citation_ids": [f"SRC_{event_id}"],
            }
        ],
    }
    if source_weight is not None:
        event["source_weight"] = source_weight
    return event


def _structured_radar_source_event(
    event_id: str,
    source_type: str,
    source_url: str,
    stock_codes: list[str],
) -> dict:
    return {
        "event_id": event_id,
        "source_type": source_type,
        "event_time": "2026-05-28T10:00:00+08:00",
        "ingested_at": "2026-05-28T10:01:00+08:00",
        "title": f"机器人执行器结构化来源 {event_id}",
        "summary": "订单和执行器供应链事件共同指向机器人执行器叙事。",
        "source_url": source_url,
        "stock_codes": stock_codes,
        "narrative_hints": ["机器人执行器"],
        "extracted_entities": {
            "tickers": stock_codes,
            "sectors": ["机器人"],
            "concepts": ["执行器"],
            "keywords": ["订单", "执行器"],
        },
        "source_metadata": {
            "provider": "gateway_news_briefs",
            "permission_status": "licensed",
            "degradation_state": "available",
        },
    }


def _seed_candidate_radar_event() -> dict:
    event = _structured_radar_source_event(
        "EVT_SEED_RADAR",
        "news",
        "gateway://news/seed-radar",
        ["300124"],
    )
    return {
        **event,
        "title": "机器人执行器 seed radar source",
        "candidate_narratives": [
            {
                "candidate_narrative_id": "C_SEED",
                "name": "机器人执行器",
                "confidence": 0.77,
                "representative_citation_ids": ["SRC_SEED_RADAR"],
                "trust_status": "candidate_untrusted",
            }
        ],
    }


def _start(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def _get_json(url: str):
    with urlopen(url, timeout=2) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _get_text(url: str) -> str:
    with urlopen(url, timeout=2) as response:  # noqa: S310
        assert response.headers.get_content_type() == "text/html"
        return response.read().decode("utf-8")


def _get_json_error(url: str):
    try:
        _get_json(url)
    except HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected HTTP error")


def _post_json(url: str, payload: dict):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=2) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _post_json_error(url: str, payload: dict):
    try:
        _post_json(url, payload)
    except HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected HTTP error")
