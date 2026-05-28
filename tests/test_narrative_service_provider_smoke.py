import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from scripts import run_narrative_service_provider_smoke


def test_narrative_service_provider_smoke_uses_fake_http_service(tmp_path):
    server = _FakeNarrativeService(("127.0.0.1", 0), _FakeNarrativeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        exit_code = run_narrative_service_provider_smoke.main(
            [
                "--base-url",
                base_url,
                "--output-dir",
                str(tmp_path),
            ]
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    payload = json.loads(
        (tmp_path / "narrative_service_provider_smoke.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["source"] == "narrative_service"
    assert payload["result"]["provider"] == "fake-narrative-service"
    assert payload["result"]["registry_count"] == 1
    assert payload["result"]["mapping_count"] == 1


def test_narrative_service_provider_smoke_discloses_local_fallback(tmp_path):
    exit_code = run_narrative_service_provider_smoke.main(
        [
            "--base-url",
            "http://127.0.0.1:9",
            "--timeout-seconds",
            "0.1",
            "--output-dir",
            str(tmp_path),
        ]
    )

    payload = json.loads(
        (tmp_path / "narrative_service_provider_smoke.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert payload["result"]["status"] == "completed"
    assert payload["result"]["source"] == "local_prototype"
    assert payload["result"]["warning_codes"][0] == "NARRATIVE_SERVICE_FALLBACK"


class _FakeNarrativeService(HTTPServer):
    allow_reuse_address = True


class _FakeNarrativeHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        data = _data_for_path(self.path)
        if data is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(_envelope(data)).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        del format
        del args


def _data_for_path(path: str):
    if path == "/api/v1/narratives/registry":
        return {
            "version": "registry-v1",
            "narratives": [{"narrative_id": "N_FAKE", "name": "Fake Narrative"}],
            "candidate_narratives": [],
            "trust_metadata": {"trust_status": "trusted_validated"},
        }
    if path == "/api/v1/narratives/mappings":
        return {
            "mappings": [
                {
                    "stock_code": "600519",
                    "narrative_id": "N_FAKE",
                    "confidence": 0.9,
                }
            ]
        }
    if path in {
        "/api/v1/narratives/evidence-packs",
        "/api/v1/narratives/candidates",
        "/api/v1/narratives/trust-audits/latest",
        "/api/v1/narratives/review-queue",
    }:
        return {}
    return None


def _envelope(data):
    return {
        "status": "available",
        "source": "narrative_service",
        "provider": "fake-narrative-service",
        "provider_version": "fake-v1",
        "data": data,
        "warnings": [],
        "trust_metadata": {"trust_status": "trusted_validated"},
    }

