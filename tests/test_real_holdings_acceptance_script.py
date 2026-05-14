import json
from pathlib import Path

import pytest
from scripts import validate_real_holdings_acceptance


def test_real_holdings_acceptance_script_passes_with_mocked_cli(
    tmp_path,
    monkeypatch,
    capsys,
):
    calls = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        if args[:2] == ["--fund-code", "161725"]:
            _write_real_holdings_outputs(tmp_path)
        return 0

    monkeypatch.setattr(validate_real_holdings_acceptance.pipeline_main, "main", fake_main)

    exit_code = validate_real_holdings_acceptance.main(["--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Real holdings acceptance passed:" in captured.out
    assert calls == [
        [
            "--fund-code",
            "161725",
            "--provider-mode",
            "eastmoney",
            "--output-dir",
            str(tmp_path),
        ],
        ["--validate-artifact-contracts", str(tmp_path)],
    ]


def test_real_holdings_acceptance_rejects_fallback_to_mock(tmp_path):
    _write_real_holdings_outputs(
        tmp_path,
        holdings_quality="mock",
        effective_quality="mock",
        degradation_events=[
            {
                "type": "provider_fallback",
                "requested_provider_mode": "eastmoney",
                "fallback_provider_mode": "mock",
                "reason": "network unavailable",
            }
        ],
    )

    with pytest.raises(validate_real_holdings_acceptance.AcceptanceError) as exc:
        validate_real_holdings_acceptance.validate_acceptance_outputs(tmp_path)

    assert "raw fund provider must be Eastmoney" in str(exc.value)


def _write_real_holdings_outputs(
    output_dir: Path,
    holdings_quality: str = "fresh",
    effective_quality: str = "partial",
    degradation_events: list[dict[str, str]] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    degradation_events = degradation_events or []
    source_url = (
        "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition?FCODE=161725"
        if holdings_quality == "fresh"
        else "mock://fixtures/fund_161725.json"
    )
    holdings_layer = {
        "layer": "holdings",
        "display_name": "Holdings",
        "provider_name": "eastmoney-fundmobapi"
        if holdings_quality == "fresh"
        else "mock-fixture-provider",
        "provider_version": "eastmoney-v1"
        if holdings_quality == "fresh"
        else "mock-v1",
        "data_quality": holdings_quality,
        "source_url": source_url,
        "is_mock": holdings_quality != "fresh",
        "note": "Fund holdings fetched from Eastmoney.",
    }
    provider_foundation = {
        "effective_data_quality": effective_quality,
        "disclosure_required": True,
        "disclosure_message": "混合数据源：Holdings 来自 Eastmoney；Evidence 使用 Mock fixtures。",
        "layers": {
            "holdings": holdings_layer,
            "narrative_registry": _mock_layer("narrative_registry"),
            "stock_mappings": _mock_layer("stock_mappings"),
            "evidence": _mock_layer("evidence"),
            "signals": _mock_layer("signals"),
        },
        "degradation_events": degradation_events,
    }
    raw = {
        "metadata": {
            "fund_code": "161725",
            "as_of_date": "2026-03-31",
            "data_quality": effective_quality,
        },
        "fund": {
            "fund_code": "161725",
            "provider_metadata": {
                "provider_name": holdings_layer["provider_name"],
                "data_quality": holdings_quality,
                "source_url": source_url,
            },
        },
        "provider_foundation": provider_foundation,
        "holdings": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "weight": 0.1833,
            }
        ],
        "degradation_events": degradation_events,
    }
    scoring = {
        "metadata": {
            "fund_code": "161725",
            "as_of_date": "2026-03-31",
            "data_quality": effective_quality,
        },
        "provider_foundation": provider_foundation,
        "candidate_review_queue": {
            "version": "candidate-review-queue-v1",
            "summary": {"total_count": 0, "pending_count": 0, "action_required": False},
            "items": [],
        },
        "degradation_events": degradation_events,
    }
    review_queue = {
        "metadata": scoring["metadata"],
        "fund": raw["fund"],
        "provider_foundation": provider_foundation,
        "candidate_review_queue": scoring["candidate_review_queue"],
        "candidate_narratives": [],
        "excluded_mapping_candidates": [],
    }
    source_table = {
        "version": "source-table-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_foundation": provider_foundation,
        "layers": list(provider_foundation["layers"].values()),
        "degradation_events": degradation_events,
    }
    manifest = {
        "version": "pipeline-artifact-manifest-v1",
        "fund_code": "161725",
        "as_of_date": "2026-03-31",
        "provider_mode": "eastmoney",
        "data_quality": effective_quality,
        "web_ready": True,
        "provider_foundation": provider_foundation,
        "degradation_events": degradation_events,
        "artifacts": {
            "raw": {"path": "fund_161725_raw.json", "format": "json"},
            "scoring": {"path": "fund_161725_scoring.json", "format": "json"},
            "review_queue": {
                "path": "fund_161725_review_queue.json",
                "format": "json",
            },
            "source_table": {
                "path": "fund_161725_source_table.json",
                "format": "json",
            },
            "markdown": {"path": "fund_161725_report.md", "format": "markdown"},
            "html": {"path": "fund_161725_report.html", "format": "html"},
        },
    }
    _write_json(output_dir / "fund_161725_raw.json", raw)
    _write_json(output_dir / "fund_161725_scoring.json", scoring)
    _write_json(output_dir / "fund_161725_review_queue.json", review_queue)
    _write_json(output_dir / "fund_161725_source_table.json", source_table)
    _write_json(output_dir / "fund_161725_manifest.json", manifest)
    (output_dir / "fund_161725_report.md").write_text(
        "Data Source Notice\n混合数据源\nEastmoney\nMock fixtures\n",
        encoding="utf-8",
    )
    (output_dir / "fund_161725_report.html").write_text(
        "Data Source Notice\n混合数据源\nEastmoney\nMock fixtures\n",
        encoding="utf-8",
    )


def _mock_layer(layer: str) -> dict:
    return {
        "layer": layer,
        "display_name": layer.replace("_", " ").title(),
        "provider_name": "mock-fixture-provider",
        "provider_version": "mock-v1",
        "data_quality": "mock",
        "source_url": f"mock://fixtures/{layer}.json",
        "is_mock": True,
        "note": "V1 Mock fixture layer.",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
