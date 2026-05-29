from __future__ import annotations

import json

from scripts import run_narrative_quality_audit


def test_run_narrative_quality_audit_writes_json_and_chinese_html(tmp_path):
    events_path = tmp_path / "events.json"
    events_path.write_text(
        json.dumps(
            {
                "version": "candidate-narrative-events-v1",
                "events": [
                    {
                        "event_id": "EVT_QUALITY_AUDIT_OK",
                        "source_type": "news",
                        "event_time": "2026-05-28T10:00:00+08:00",
                        "ingested_at": "2026-05-28T10:01:00+08:00",
                        "source_url": "gateway://news/quality-audit-ok",
                        "stock_codes": ["300124"],
                        "extraction_confidence": 0.86,
                        "claim_type": "demand",
                        "claim_polarity": "positive",
                        "extracted_entities": {
                            "tickers": ["300124"],
                            "sectors": ["机器人"],
                            "concepts": ["执行器"],
                            "keywords": ["订单"],
                        },
                        "source_metadata": {
                            "provider": "gateway_news_briefs",
                            "permission_status": "licensed",
                            "degradation_state": "available",
                        },
                        "candidate_narratives": [
                            {
                                "candidate_narrative_id": "C_AUDIT_OK",
                                "name": "机器人执行器",
                                "confidence": 0.86,
                                "representative_citation_ids": [
                                    "EVT_QUALITY_AUDIT_OK"
                                ],
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = run_narrative_quality_audit.main(
        [
            "--candidate-events-path",
            str(events_path),
            "--as-of",
            "2026-05-29T00:00:00+08:00",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads((tmp_path / "narrative_quality_audit.json").read_text())
    html = (tmp_path / "narrative_quality_audit.html").read_text(encoding="utf-8")

    assert exit_code == 0
    assert payload["version"] == "narrative-quality-audit-v1"
    assert payload["export_manifest"]["formula_version"] == (
        "evidence-quality-deterministic-v1"
    )
    assert payload["summary"]["narrative_count"] == 1
    assert "叙事质量审计工作台" in html
    assert "C_AUDIT_OK" in html
