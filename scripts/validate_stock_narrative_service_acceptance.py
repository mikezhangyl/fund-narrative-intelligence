from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_SRC = PROJECT_ROOT / "services" / "stock-narrative-service" / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from scripts import run_narrative_service_conformance_probe  # noqa: E402
from scripts import run_narrative_service_provider_smoke  # noqa: E402
from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.providers.narrative_service import build_narrative_data_provider  # noqa: E402
from src.scanners.fund_holding_exposure_report import (  # noqa: E402
    FundHoldingExposureConfig,
    execute_fund_holding_exposure_report,
    render_html_report,
)
from stock_narrative_service.app import create_server  # noqa: E402
from stock_narrative_service.config import ServiceConfig  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate in-repo Stock Narrative Service against FNI."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = ServiceConfig(
        intake_ledger_path=output_dir / "runtime" / "candidate_intake_events.json",
        review_actions_path=output_dir / "runtime" / "review_actions.json",
        promotion_decisions_path=output_dir / "runtime" / "promotion_decisions.json",
    )
    server = create_server((args.host, args.port), config=config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://{args.host}:{server.server_port}"
        result = _run_acceptance(base_url=base_url, output_dir=output_dir)
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
    _write_summary(output_dir=output_dir, result=result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


def _run_acceptance(*, base_url: str, output_dir: Path) -> dict[str, Any]:
    conformance_dir = output_dir / "conformance"
    provider_smoke_dir = output_dir / "provider_smoke"
    provider_fallback_smoke_dir = output_dir / "provider_fallback_smoke"
    conformance_exit = run_narrative_service_conformance_probe.main(
        ["--base-url", base_url, "--output-dir", str(conformance_dir)]
    )
    provider_smoke_exit = run_narrative_service_provider_smoke.main(
        ["--base-url", base_url, "--output-dir", str(provider_smoke_dir)]
    )
    fallback_smoke_exit = run_narrative_service_provider_smoke.main(
        [
            "--base-url",
            "http://127.0.0.1:9",
            "--timeout-seconds",
            "0.1",
            "--output-dir",
            str(provider_fallback_smoke_dir),
        ]
    )
    conformance = _read_result(
        conformance_dir / "narrative_service_conformance_report.json"
    )
    provider_smoke = _read_result(
        provider_smoke_dir / "narrative_service_provider_smoke.json"
    )
    fallback_smoke = _read_result(
        provider_fallback_smoke_dir / "narrative_service_provider_smoke.json"
    )
    report = _build_service_backed_report(base_url=base_url)
    _write_report(output_dir=output_dir, report=report)
    return {
        "version": "stock-narrative-service-acceptance-v1",
        "generated_at": _now(),
        "status": _status(
            conformance_exit=conformance_exit,
            provider_smoke_exit=provider_smoke_exit,
            fallback_smoke_exit=fallback_smoke_exit,
            conformance=conformance,
            provider_smoke=provider_smoke,
            fallback_smoke=fallback_smoke,
            report=report,
        ),
        "base_url": base_url,
        "ci_gate": _ci_gate(),
        "conformance_status": str(conformance.get("status") or ""),
        "provider_smoke_status": str(provider_smoke.get("status") or ""),
        "provider_smoke_source": str(provider_smoke.get("source") or ""),
        "fallback_smoke_status": str(fallback_smoke.get("status") or ""),
        "fallback_smoke_source": str(fallback_smoke.get("source") or ""),
        "fallback_smoke_warning_codes": [
            str(code)
            for code in fallback_smoke.get("warning_codes", [])
            if str(code)
        ],
        "report_status": str(report.get("status") or ""),
        "report_narrative_source": str(
            _mapping(report.get("narrative_source")).get("source") or ""
        ),
        "artifacts": {
            "conformance": str(
                conformance_dir / "narrative_service_conformance_report.json"
            ),
            "provider_smoke": str(
                provider_smoke_dir / "narrative_service_provider_smoke.json"
            ),
            "provider_fallback_smoke": str(
                provider_fallback_smoke_dir / "narrative_service_provider_smoke.json"
            ),
            "report_json": str(output_dir / "fund_holding_exposure_report.json"),
            "report_html": str(output_dir / "fund_holding_exposure_report.html"),
        },
    }


def _build_service_backed_report(*, base_url: str) -> dict[str, Any]:
    snapshot = build_narrative_data_provider(base_url=base_url).get_snapshot()
    return execute_fund_holding_exposure_report(
        data_source=_AcceptanceFundSource(),
        config=FundHoldingExposureConfig(
            fund_code="ACCEPTANCE_FUND",
            limit=10,
            sector_universe_limit=0,
        ),
        narrative_registry=snapshot["narrative_registry"],
        stock_narrative_mappings=snapshot["stock_narrative_mappings"],
        narrative_source={
            "source": snapshot["source"],
            "provider": snapshot["provider"],
            "provider_version": snapshot["provider_version"],
            "data_fetch_mode": snapshot["source"],
            "warnings": snapshot.get("warnings", []),
            "diagnostics": snapshot.get("diagnostics", {}),
        },
    )


class _AcceptanceFundSource:
    degradation_events: list[dict[str, Any]] = []

    def fetch_fund_profile(self, *, fund_code: str) -> list[dict[str, Any]]:
        return [
            {
                "fund_code": fund_code,
                "fund_name": "Narrative Service Acceptance Fund",
                "fund_type": "acceptance_fixture",
                "currency": "CNY",
                "source": "acceptance_fixture",
            }
        ]

    def fetch_fund_holdings(self, *, fund_code: str, limit: int) -> list[dict[str, Any]]:
        rows = [
            {
                "fund_code": fund_code,
                "as_of_date": "2026-05-29",
                "stock_code": "600519",
                "ts_code": "600519.SH",
                "stock_name": "贵州茅台",
                "weight": 0.18,
                "industry": "食品饮料",
                "source": "acceptance_fixture",
            },
            {
                "fund_code": fund_code,
                "as_of_date": "2026-05-29",
                "stock_code": "000063",
                "ts_code": "000063.SZ",
                "stock_name": "中兴通讯",
                "weight": 0.12,
                "industry": "通信",
                "source": "acceptance_fixture",
            },
        ]
        return rows[:limit]

    def fetch_stock_sector_memberships(
        self,
        *,
        symbols: list[str],
        trade_date: str | None,
        sector_types: list[str],
        limit_per_symbol: int,
        sector_universe_limit: int | None,
    ) -> list[dict[str, Any]]:
        del trade_date
        del limit_per_symbol
        del sector_universe_limit
        rows = [
            {
                "symbol": "600519.SH",
                "sector_name": "白酒概念",
                "sector_type": sector_types[0],
                "source": "acceptance_fixture",
            },
            {
                "symbol": "000063.SZ",
                "sector_name": "通信设备",
                "sector_type": sector_types[0],
                "source": "acceptance_fixture",
            },
        ]
        requested = set(symbols)
        return [row for row in rows if row["symbol"] in requested]


def _status(
    *,
    conformance_exit: int,
    provider_smoke_exit: int,
    fallback_smoke_exit: int,
    conformance: dict[str, Any],
    provider_smoke: dict[str, Any],
    fallback_smoke: dict[str, Any],
    report: dict[str, Any],
) -> str:
    if (
        conformance_exit == 0
        and provider_smoke_exit == 0
        and fallback_smoke_exit == 0
        and conformance.get("status") == "completed"
        and provider_smoke.get("status") == "completed"
        and provider_smoke.get("source") == "narrative_service"
        and fallback_smoke.get("status") == "completed"
        and fallback_smoke.get("source") == "local_prototype"
        and "NARRATIVE_SERVICE_FALLBACK" in fallback_smoke.get("warning_codes", [])
        and report.get("status") in {"completed", "partial"}
        and _mapping(report.get("narrative_source")).get("source")
        == "narrative_service"
    ):
        return "completed"
    return "failed"


def _ci_gate() -> dict[str, Any]:
    return {
        "mode": "deterministic_local",
        "requires_live_credentials": False,
        "mandatory_slice_checks": [
            "contract_endpoint_conformance",
            "provider_smoke_service_first",
            "provider_smoke_local_fallback",
            "service_backed_report_source_disclosure",
        ],
        "full_release_checks": [
            "uv run pytest -q",
            "uv run python scripts/validate_stock_narrative_service_acceptance.py",
            "live_gateway_provider_checks_when_credentials_exist",
        ],
        "output_policy": {
            "default_root": "outputs/stock_narrative_service_acceptance/",
            "source_control": "generated_outputs_ignored",
        },
    }


def _read_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"{path} missing result object")
    return result


def _write_report(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "fund_holding_exposure_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "fund_holding_exposure_report.html").write_text(
        render_html_report(report),
        encoding="utf-8",
    )


def _write_summary(*, output_dir: Path, result: dict[str, Any]) -> None:
    (output_dir / "acceptance_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _default_output_dir() -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / "stock_narrative_service_acceptance" / timestamp


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
