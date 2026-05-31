from __future__ import annotations

import json

from scripts import run_source_reliability_report as report_script
from src.scanners.source_reliability import (
    load_source_reliability_scoring_policy,
    score_source_reliability,
    score_source_reliability_inventory,
)


def _source(**overrides):
    source = {
        "source_id": "sec_edgar_filings",
        "display_name": "SEC EDGAR filings",
        "source_class": "official_disclosure",
        "license_scope": "metadata_and_public_document_reference",
        "anti_bot_risk": "low",
        "governance_gate_status": "passed",
        "corroborating_evidence": True,
        "dimension_scores": {
            "availability": 0.95,
            "latency_freshness": 0.9,
            "schema_stability": 0.9,
            "completeness": 0.85,
            "entity_tagging_quality": 0.8,
            "license_clarity": 0.95,
            "anti_bot_risk": 0.95,
            "retry_recoverability": 0.8,
            "historical_depth": 0.85,
            "operational_cost": 0.9,
            "contradiction_rate": 0.9,
        },
    }
    return {**source, **overrides}


def test_source_reliability_policy_declares_dimensions_and_labels():
    policy = load_source_reliability_scoring_policy()

    assert policy["version"] == "source-reliability-scoring-v1"
    assert set(policy["dimensions"]) >= {
        "availability",
        "latency_freshness",
        "schema_stability",
        "completeness",
        "entity_tagging_quality",
        "license_clarity",
        "anti_bot_risk",
        "retry_recoverability",
        "historical_depth",
        "operational_cost",
        "contradiction_rate",
    }
    assert policy["labels"] == [
        "Trusted Fact",
        "Licensed News",
        "Research Context",
        "Heat Signal",
        "Experimental",
        "Avoid",
    ]


def test_official_disclosure_scores_as_trusted_fact():
    result = score_source_reliability(_source())

    assert result["label"] == "Trusted Fact"
    assert result["score"] >= 0.8
    assert result["display_allowed"] is True


def test_licensed_news_scores_as_licensed_news():
    result = score_source_reliability(
        _source(
            source_id="licensed_reuters",
            source_class="licensed_news",
            license_scope="licensed_news_api",
        )
    )

    assert result["label"] == "Licensed News"


def test_social_source_without_corroboration_is_heat_signal_not_trusted_fact():
    result = score_source_reliability(
        _source(
            source_id="stocktwits_heat",
            source_class="social_community",
            license_scope="metadata_and_permitted_excerpt",
            corroborating_evidence=False,
        )
    )

    assert result["label"] == "Heat Signal"
    assert "social_sources_require_corroboration_for_trusted_fact" in result["warnings"]
    assert result["label"] != "Trusted Fact"


def test_blocked_or_high_risk_source_scores_avoid():
    result = score_source_reliability(
        _source(
            source_id="blocked_scrape",
            governance_gate_status="blocked",
            anti_bot_risk="high",
        )
    )

    assert result["label"] == "Avoid"
    assert result["display_allowed"] is False


def test_source_reliability_inventory_report_outputs_json_and_chinese_html(tmp_path):
    input_path = tmp_path / "inventory.json"
    input_path.write_text(
        json.dumps(
            {
                "sources": [
                    _source(),
                    _source(
                        source_id="stocktwits_heat",
                        source_class="social_community",
                        license_scope="metadata_and_permitted_excerpt",
                        corroborating_evidence=False,
                    ),
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = report_script.main(
        ["--input", str(input_path), "--output-dir", str(tmp_path / "out")]
    )

    assert exit_code == 0
    payload = json.loads((tmp_path / "out" / "source_reliability_report.json").read_text())
    html = (tmp_path / "out" / "source_reliability_report.html").read_text()

    assert payload["summary"]["source_count"] == 2
    assert payload["summary"]["label_counts"]["Trusted Fact"] == 1
    assert payload["summary"]["label_counts"]["Heat Signal"] == 1
    assert "来源可靠性评分报告" in html
    assert "Trusted Fact" in html
    assert "Heat Signal" in html
    assert "stocktwits_heat" in html


def test_score_source_reliability_inventory_counts_labels():
    inventory = {"sources": [_source(), _source(source_id="bad", governance_gate_status="blocked")]}

    report = score_source_reliability_inventory(inventory)

    assert report["summary"]["source_count"] == 2
    assert report["summary"]["label_counts"]["Trusted Fact"] == 1
    assert report["summary"]["label_counts"]["Avoid"] == 1
