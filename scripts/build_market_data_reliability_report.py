from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CAPABILITY_REPORT = (
    PROJECT_ROOT / "outputs" / "data_capabilities" / "data_capability_report.json"
)
DEFAULT_RUNTIME_REPORT = (
    PROJECT_ROOT / "outputs" / "data_capabilities" / "market_data_runtime_report.json"
)
DEFAULT_LIVE_REPORT = (
    PROJECT_ROOT
    / "outputs"
    / "market_data_live_validation"
    / "2026-05-25-data-capability-registry"
    / "live_validation_report.json"
)
DEFAULT_STRESS_REPORT = (
    PROJECT_ROOT
    / "outputs"
    / "market_data_stress"
    / "2026-05-25-controlled-v0"
    / "stress_report.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a consolidated V0 market-data reliability report."
    )
    parser.add_argument("--capabilities", type=Path, default=DEFAULT_CAPABILITY_REPORT)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME_REPORT)
    parser.add_argument("--live-validation", type=Path, default=DEFAULT_LIVE_REPORT)
    parser.add_argument("--stress", type=Path, default=DEFAULT_STRESS_REPORT)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        dest="output_format",
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_reliability_report(
        capability_report=_read_json(args.capabilities),
        runtime_report=_read_json(args.runtime),
        live_report=_read_json(args.live_validation),
        stress_report=_read_json(args.stress),
    )
    rendered = render_report(report, output_format=args.output_format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


def build_reliability_report(
    *,
    capability_report: dict[str, Any],
    runtime_report: dict[str, Any],
    live_report: dict[str, Any],
    stress_report: dict[str, Any],
) -> dict[str, Any]:
    live_summary = _live_summary(live_report)
    stress_summary = _stress_summary(stress_report)
    analysis_readiness = _analysis_readiness_summary(capability_report)
    recommendations = _recommendations(
        capability_report=capability_report,
        runtime_report=runtime_report,
        live_summary=live_summary,
        stress_summary=stress_summary,
        analysis_readiness=analysis_readiness,
    )
    return {
        "version": "market-data-reliability-report-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": _overall_status(
            live_summary=live_summary,
            stress_summary=stress_summary,
            analysis_readiness=analysis_readiness,
        ),
        "runtime": _runtime_summary(runtime_report),
        "capabilities": _capability_summary(capability_report),
        "analysis_readiness": analysis_readiness,
        "live_validation": live_summary,
        "stress": stress_summary,
        "recommendations": recommendations,
    }


def render_report(report: dict[str, Any], *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output_format == "markdown":
        return _markdown_report(report)
    raise ValueError(f"unsupported output format: {output_format}")


def _runtime_summary(report: dict[str, Any]) -> dict[str, Any]:
    providers = {provider["provider"]: provider for provider in report.get("providers", [])}
    tushare = providers.get("tushare", {})
    return {
        "cache_dir_exists": bool(report.get("default_cache_dir_exists")),
        "request_log_path_exists": bool(report.get("request_log_path_exists")),
        "gateway_configured": bool((report.get("gateway") or {}).get("base_url_configured")),
        "gateway_url_kind": (report.get("gateway") or {}).get("base_url_kind"),
        "tushare_api_url_kind": tushare.get("api_url_kind"),
        "tushare_token_configured": bool((tushare.get("token") or {}).get("configured")),
        "tushare_token_source": (tushare.get("token") or {}).get("source"),
    }


def _capability_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") or {}
    if not summary:
        datasets = report.get("datasets", {})
        summary = {
            "dataset_count": len(datasets),
            "missing_or_planned_datasets": [
                key
                for key, dataset in datasets.items()
                if dataset.get("current_status") in {"missing", "planned"}
            ],
        }
    return {
        "dataset_count": int(summary.get("dataset_count", 0)),
        "dataset_status_counts": summary.get("dataset_status_counts", {}),
        "gateway_mode_counts": summary.get("gateway_mode_counts", {}),
        "missing_or_planned_datasets": summary.get("missing_or_planned_datasets", []),
    }


def _analysis_readiness_summary(report: dict[str, Any]) -> dict[str, Any]:
    readiness = report.get("analysis_readiness", {})
    blocked = [
        key for key, value in readiness.items() if not bool(value.get("can_run"))
    ]
    warnings = {
        key: value.get("warnings", [])
        for key, value in readiness.items()
        if value.get("warnings")
    }
    return {
        "total": len(readiness),
        "runnable": len(readiness) - len(blocked),
        "blocked": blocked,
        "warnings": warnings,
    }


def _live_summary(report: dict[str, Any]) -> dict[str, Any]:
    checks = report.get("checks", [])
    failed = [check for check in checks if check.get("availability") is not True]
    return {
        "generated_at": report.get("generated_at"),
        "total_checks": len(checks),
        "available_checks": len(checks) - len(failed),
        "failed_checks": len(failed),
        "failed_capabilities": [
            {
                "capability": check.get("capability"),
                "source": check.get("source"),
                "endpoint": check.get("endpoint"),
                "failure_reason": check.get("failure_reason"),
            }
            for check in failed
        ],
    }


def _stress_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    results = report.get("results", {})
    failed_tests = [
        {
            "test": name,
            "failure_count": result.get("failure_count", 0),
            "failure_reasons": result.get("failure_reasons", []),
        }
        for name, result in results.items()
        if int(result.get("failure_count", 0)) > 0
    ]
    return {
        "generated_at": report.get("generated_at"),
        "status": report.get("status"),
        "test_count": int(summary.get("test_count", 0)),
        "request_volume": int(summary.get("request_volume", 0)),
        "rows_returned": int(summary.get("rows_returned", 0)),
        "failure_count": int(summary.get("failure_count", 0)),
        "failed_tests": failed_tests,
    }


def _overall_status(
    *,
    live_summary: dict[str, Any],
    stress_summary: dict[str, Any],
    analysis_readiness: dict[str, Any],
) -> str:
    if live_summary["failed_checks"] or stress_summary["failure_count"]:
        return "degraded"
    if analysis_readiness["blocked"]:
        return "partial"
    return "ready"


def _recommendations(
    *,
    capability_report: dict[str, Any],
    runtime_report: dict[str, Any],
    live_summary: dict[str, Any],
    stress_summary: dict[str, Any],
    analysis_readiness: dict[str, Any],
) -> list[str]:
    recommendations: list[str] = []
    runtime = _runtime_summary(runtime_report)
    if runtime["tushare_api_url_kind"] == "official_default":
        recommendations.append(
            "Keep TUSHARE_API_URL configurable; switch it to the local gateway once the gateway service is ready."
        )
    if live_summary["failed_checks"]:
        failed = ", ".join(
            str(item["capability"]) for item in live_summary["failed_capabilities"]
        )
        recommendations.append(f"Stabilize or isolate failed live probes: {failed}.")
    if stress_summary["failure_count"]:
        recommendations.append(
            "Treat stress failures as endpoint stability evidence and keep failure_reasons in reports."
        )
    missing = _capability_summary(capability_report)["missing_or_planned_datasets"]
    if missing:
        recommendations.append(
            "Do not build dependent analysis as production-ready until these datasets are implemented: "
            + ", ".join(missing)
            + "."
        )
    if analysis_readiness["warnings"]:
        recommendations.append(
            "Allow prototype scanners to run with warnings, but keep unstable datasets out of hard gates."
        )
    if not runtime["cache_dir_exists"]:
        recommendations.append("Create and verify the market-data cache directory before scaling scans.")
    return recommendations


def _markdown_report(report: dict[str, Any]) -> str:
    runtime = report["runtime"]
    capabilities = report["capabilities"]
    readiness = report["analysis_readiness"]
    live = report["live_validation"]
    stress = report["stress"]
    lines = [
        "# V0 Market Data Reliability Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Tushare URL Kind: `{runtime.get('tushare_api_url_kind')}`",
        f"- Tushare Token: `{runtime.get('tushare_token_source')}`",
        f"- Gateway Configured: `{runtime.get('gateway_configured')}`",
        f"- Gateway URL Kind: `{runtime.get('gateway_url_kind')}`",
        f"- Cache Dir Exists: `{runtime.get('cache_dir_exists')}`",
        f"- Dataset Count: `{capabilities.get('dataset_count')}`",
        f"- Runnable Analysis Capabilities: `{readiness.get('runnable')}/{readiness.get('total')}`",
        f"- Live Checks: `{live.get('available_checks')}/{live.get('total_checks')}`",
        f"- Stress Requests: `{stress.get('request_volume')}`",
        f"- Stress Failures: `{stress.get('failure_count')}`",
        "",
        "## Failed Live Capabilities",
        "",
    ]
    if live["failed_capabilities"]:
        lines.extend(
            f"- `{item['capability']}` via `{item['source']}.{item['endpoint']}`"
            for item in live["failed_capabilities"]
        )
    else:
        lines.append("- None")
    lines.extend(["", "## Blocked Analysis Capabilities", ""])
    if readiness["blocked"]:
        lines.extend(f"- `{item}`" for item in readiness["blocked"])
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in report["recommendations"])
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"report not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"report must be a JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
