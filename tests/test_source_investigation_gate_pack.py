from __future__ import annotations

import json

from scripts import run_source_investigation_gate_pack
from src.scanners.source_investigation_gate_pack import (
    build_source_investigation_gate_pack,
    render_source_investigation_gate_pack_html,
)


def test_investigation_gate_pack_covers_remaining_pm_investigation_issues():
    pack = build_source_investigation_gate_pack(
        generated_at="2026-06-02T06:00:00+00:00",
    )

    assert pack["version"] == "source-investigation-gate-pack-v1"
    assert pack["generated_at"] == "2026-06-02T06:00:00+00:00"
    assert pack["summary"] == {
        "issue_count": 3,
        "candidate_count": 12,
        "trial_first_count": 3,
        "controlled_pilot_count": 1,
        "developer_blocked_count": 3,
    }
    assert {section["linear_id"] for section in pack["issue_sections"]} == {
        "MIK-240",
        "MIK-241",
        "MIK-242",
    }
    assert all(
        section["developer_gate"]["implementation_issue_allowed"] is False
        for section in pack["issue_sections"]
    )


def test_china_paid_provider_checklist_recommends_one_trial_candidate():
    section = _section("MIK-240")
    candidates = {candidate["source_id"]: candidate for candidate in section["candidates"]}

    assert section["recommendation"] == {
        "decision": "trial_first",
        "trial_target": "choice_financial_terminal",
        "reason": (
            "Choice has public contact/API evidence and cross-platform Python/C++ support; "
            "PM still needs vendor quote, redistribution terms, and credentialed docs."
        ),
    }
    assert candidates["choice_financial_terminal"]["decision_label"] == "Trial First"
    assert candidates["wind_financial_terminal"]["missing_information"] == [
        "news entitlement package",
        "redistribution/display terms",
        "cost band/vendor quote",
        "credentialed API docs",
    ]
    assert candidates["ifind_financial_terminal"]["endpoint_categories"] == [
        "news",
        "research/briefs",
        "sector/concept events",
        "company events",
        "macro/policy data",
        "entity tags",
    ]
    assert all(candidate["cost_band"] == "vendor_quote_required" for candidate in candidates.values())


def test_global_paid_news_checklist_has_professional_and_developer_targets():
    section = _section("MIK-241")
    candidates = {candidate["source_id"]: candidate for candidate in section["candidates"]}

    assert section["recommendation"]["professional_news_candidate"] == "lseg_reuters_news"
    assert section["recommendation"]["news_analytics_candidate"] == "ravenpack_news_analytics"
    assert section["recommendation"]["lower_cost_developer_api_candidate"] == "benzinga_news_api"
    assert section["trial_smoke_query_set"] == {
        "symbols": ["AAPL", "NVDA", "TSLA", "BABA", "TSM"],
        "topics": ["AI semiconductors", "China EV", "Fed policy", "supply chain disruption"],
        "window": "last_24h_and_last_7d",
        "required_fields": [
            "headline",
            "published_at",
            "source",
            "entity_metadata",
            "sentiment_or_event_metadata",
            "permitted_url_or_story_id",
        ],
    }
    assert "event/entity metadata" in candidates["ravenpack_news_analytics"]["metadata_support"]
    assert "REST" in candidates["benzinga_news_api"]["api_access"]


def test_china_social_access_labels_heat_only_and_never_trusted_fact():
    section = _section("MIK-242")
    labels = {candidate["source_id"]: candidate["access_label"] for candidate in section["candidates"]}

    assert labels == {
        "xueqiu": "High-risk/Do Not Crawl",
        "eastmoney_guba": "Unknown",
        "weibo": "Official API",
        "stocktwits_reference": "Commercial Access",
    }
    assert all(candidate["trust_tier"] != "trusted_fact" for candidate in section["candidates"])
    assert all(candidate["output_role"] == "heat_signal_only" for candidate in section["candidates"])
    assert section["recommendation"] == {
        "decision": "controlled_pilot_only_for_weibo_official_api",
        "reason": (
            "Only official API/commercial access can enter a controlled heat-signal pilot; "
            "Xueqiu and EastMoney Guba should not be crawled until permission is confirmed."
        ),
    }


def test_investigation_gate_pack_html_is_chinese_and_records_decisions():
    html = render_source_investigation_gate_pack_html(
        build_source_investigation_gate_pack()
    )

    assert "<h1>R13 来源调查 Gate Pack</h1>" in html
    assert "MIK-240" in html
    assert "Choice" in html
    assert "LSEG / Reuters" in html
    assert "雪球" in html
    assert "Developer work is blocked" in html
    assert "决策过程" in html


def test_source_investigation_gate_pack_cli_writes_json_and_html(tmp_path):
    exit_code = run_source_investigation_gate_pack.main(
        ["--output-dir", str(tmp_path)]
    )
    payload = json.loads((tmp_path / "source_investigation_gate_pack.json").read_text())

    assert exit_code == 0
    assert payload["summary"]["issue_count"] == 3
    assert "<h1>R13 来源调查 Gate Pack</h1>" in (
        tmp_path / "source_investigation_gate_pack.html"
    ).read_text()


def _section(linear_id: str) -> dict[str, object]:
    pack = build_source_investigation_gate_pack()
    return next(section for section in pack["issue_sections"] if section["linear_id"] == linear_id)
