import json

from scripts import run_narrative_service_conformance_probe


def test_narrative_service_conformance_probe_reports_not_configured(
    monkeypatch,
    tmp_path,
):
    monkeypatch.delenv("NARRATIVE_SERVICE_URL", raising=False)

    exit_code = run_narrative_service_conformance_probe.main(
        ["--output-dir", str(tmp_path)]
    )

    payload = json.loads(
        (tmp_path / "narrative_service_conformance_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert payload["result"]["status"] == "not_configured"
    assert payload["result"]["base_url"] == ""
    assert payload["result"]["endpoint_results"] == []


def test_narrative_service_conformance_probe_checks_contract_endpoints(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("NARRATIVE_SERVICE_URL", "http://127.0.0.1:9999")
    requested: list[tuple[str, str]] = []

    def fake_request_json(*, method, url, payload, timeout_seconds):
        del payload
        del timeout_seconds
        requested.append((method, url))
        return {
            "status": "available",
            "source": "narrative_service",
            "provider": "fake-narrative-service",
            "provider_version": "fake-v1",
            "data": {},
            "warnings": [],
            "trust_metadata": {"trust_status": "candidate_untrusted"},
        }

    monkeypatch.setattr(
        run_narrative_service_conformance_probe,
        "_request_json",
        fake_request_json,
    )

    exit_code = run_narrative_service_conformance_probe.main(
        ["--output-dir", str(tmp_path)]
    )

    payload = json.loads(
        (tmp_path / "narrative_service_conformance_report.json").read_text(
            encoding="utf-8"
        )
    )
    endpoint_results = payload["result"]["endpoint_results"]
    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert {
        result["method"] + " " + result["path"] for result in endpoint_results
    } >= {
        "GET /api/v1/narratives/registry",
        "GET /api/v1/narratives/mappings",
        "POST /api/v1/narratives/intake/events",
        "GET /api/v1/narratives/evidence-packs",
        "GET /api/v1/narratives/trust-audits/latest",
        "GET /api/v1/narratives/review-queue",
    }
    assert all(result["status"] == "passed" for result in endpoint_results)
    assert requested
    assert requested[0][1].startswith("http://127.0.0.1:9999/api/v1/narratives/")

