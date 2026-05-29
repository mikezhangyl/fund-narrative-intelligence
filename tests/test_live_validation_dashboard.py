from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

from scripts import run_live_validation_dashboard

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "stock-narrative-service"
SRC_ROOT = SERVICE_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from stock_narrative_service.app import create_server  # noqa: E402
from stock_narrative_service.config import ServiceConfig  # noqa: E402


def test_live_validation_dashboard_marks_missing_config_as_not_configured(tmp_path):
    report = run_live_validation_dashboard.build_dashboard(
        gateway_url="",
        service_url="",
        generated_at="2026-05-29T00:00:00+00:00",
        timeout_seconds=0.1,
    )

    statuses = {row["status"] for row in report["rows"]}

    assert report["taxonomy"]["statuses"] == [
        "passed",
        "degraded",
        "blocked",
        "not_configured",
        "product_gap",
        "system_failure",
    ]
    assert "not_configured" in statuses
    assert "missing_config" in report["taxonomy"]["aliases"]["not_configured"]
    assert report["summary"]["status_counts"]["not_configured"] > 0
    assert report["summary"]["system_failure_count"] == 0


def test_live_validation_taxonomy_is_documented():
    document = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "product"
        / "live-validation-dashboard-taxonomy-2026-05-29.md"
    )
    text = document.read_text(encoding="utf-8")

    for term in [
        "passed",
        "degraded",
        "blocked",
        "not_configured",
        "product_gap",
        "system_failure",
        "MARKET_DATA_GATEWAY_URL",
        "NARRATIVE_SERVICE_URL",
        "bounded",
        "live gateway/provider checks",
    ]:
        assert term in text


def test_live_validation_dashboard_classifies_gateway_and_service_rows_with_fake_fetcher():
    report = run_live_validation_dashboard.build_dashboard(
        gateway_url="http://gateway.local",
        service_url="http://service.local",
        generated_at="2026-05-29T00:00:00+00:00",
        timeout_seconds=0.1,
        fetch_json=_fake_fetch_json,
    )
    rows = {row["capability"]: row for row in report["rows"]}

    assert rows["gateway_configuration"]["status"] == "passed"
    assert rows["gateway_fund_holdings"]["status"] == "passed"
    assert rows["gateway_daily_bars"]["status"] == "passed"
    assert rows["gateway_sector_flow_structure_news"]["status"] == "degraded"
    assert rows["narrative_service_health"]["status"] == "passed"
    assert rows["narrative_service_ops"]["status"] == "passed"
    assert rows["narrative_review_workspace"]["status"] == "passed"
    assert report["summary"]["live_provider_check_count"] >= 6
    assert report["summary"]["deterministic_check_count"] >= 1


def test_live_validation_dashboard_writes_json_and_chinese_html(tmp_path):
    report = run_live_validation_dashboard.build_dashboard(
        gateway_url="",
        service_url="",
        generated_at="2026-05-29T00:00:00+00:00",
        timeout_seconds=0.1,
    )

    outputs = run_live_validation_dashboard.write_outputs(
        output_dir=tmp_path,
        report=report,
    )

    payload = json.loads(Path(outputs["json"]).read_text(encoding="utf-8"))
    html = Path(outputs["html"]).read_text(encoding="utf-8")

    assert payload["version"] == "live-validation-dashboard-v1"
    assert "实时验证看板" in html
    assert "缺少配置" in html
    assert "not_configured" in html


def test_live_validation_dashboard_checks_running_narrative_service(tmp_path):
    server = create_server(("127.0.0.1", 0), config=ServiceConfig())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = run_live_validation_dashboard.build_dashboard(
            gateway_url="",
            service_url=f"http://127.0.0.1:{server.server_port}",
            generated_at="2026-05-29T00:00:00+00:00",
            timeout_seconds=2.0,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    rows = {row["capability"]: row for row in report["rows"]}
    assert rows["narrative_service_health"]["status"] == "passed"
    assert rows["narrative_service_ops"]["status"] == "passed"
    assert rows["narrative_review_workspace"]["status"] in {"passed", "product_gap"}


def _fake_fetch_json(
    *,
    method: str,
    url: str,
    payload: dict[str, object] | None,
    timeout_seconds: float,
) -> tuple[int, dict[str, object]]:
    del method, payload, timeout_seconds
    path = urlparse(url).path
    if path == "/api/health":
        return 200, {"status": "ok", "service": "stock-narrative-service"}
    if path.endswith("/ops/summary"):
        return 200, {"status": "ok", "data": {"diagnostics": {"warning_count": 0}}}
    if path.endswith("/review-queue"):
        return 200, {"status": "ok", "data": {"items": [{"payload_ref": "C_SEED"}]}}
    if path.endswith("/funds/holdings"):
        return 200, {"data": {"rows": [{"fund_code": "161725", "stock_code": "600519"}]}}
    if path.endswith("/tushare/daily"):
        return 200, {"data": {"rows": [{"symbol": "600519.SH", "close": 100.0}]}}
    if path.endswith("/news/briefs"):
        return 200, {"status": "degraded", "data": {"rows": []}, "warnings": [{"code": "UPSTREAM_TIMEOUT"}]}
    return 200, {"data": {"rows": [{"ok": True}]}}
