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
    promotion_decisions_path = tmp_path / "runtime" / "promotion_decisions.json"
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
