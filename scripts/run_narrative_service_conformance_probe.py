from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.config import PROJECT_ROOT as CONFIG_PROJECT_ROOT  # noqa: E402

DEFAULT_CONTRACT_PATH = CONFIG_PROJECT_ROOT / "config" / "narrative_service_contract.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a future Narrative Service conformance probe."
    )
    parser.add_argument("--base-url", default=os.environ.get("NARRATIVE_SERVICE_URL", ""))
    parser.add_argument("--contract-path", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = _load_contract(args.contract_path)
    base_url = args.base_url.strip().rstrip("/")
    result = (
        _not_configured_result(contract=contract)
        if not base_url
        else _probe_contract(
            contract=contract,
            base_url=base_url,
            timeout_seconds=args.timeout_seconds,
        )
    )
    report = {
        "version": "narrative-service-conformance-probe-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "result": result,
    }
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "narrative_service_conformance_report.json"),
                "markdown": str(output_dir / "narrative_service_conformance_report.md"),
                "status": result["status"],
                "endpoint_count": len(result["endpoint_results"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["status"] in {"completed", "partial", "not_configured"} else 1


def _load_contract(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload


def _not_configured_result(*, contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability": "narrative_service_conformance",
        "status": "not_configured",
        "data_fetch_mode": "narrative_service",
        "base_url": "",
        "contract_version": str(contract.get("version") or ""),
        "endpoint_results": [],
        "failures": [
            {
                "capability": "narrative_service",
                "reason": "NARRATIVE_SERVICE_URL is not configured.",
            }
        ],
    }


def _probe_contract(
    *,
    contract: dict[str, Any],
    base_url: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    required_fields = _required_envelope_fields(contract)
    endpoint_results = [
        _probe_endpoint(
            base_url=base_url,
            endpoint=endpoint,
            required_fields=required_fields,
            timeout_seconds=timeout_seconds,
        )
        for endpoint in contract.get("endpoints", [])
        if isinstance(endpoint, dict)
    ]
    failures = [
        {
            "capability": result["path"],
            "reason": result["reason"],
        }
        for result in endpoint_results
        if result["status"] != "passed"
    ]
    return {
        "capability": "narrative_service_conformance",
        "status": _status(endpoint_results),
        "data_fetch_mode": "narrative_service",
        "base_url": base_url,
        "contract_version": str(contract.get("version") or ""),
        "endpoint_results": endpoint_results,
        "failures": failures,
    }


def _probe_endpoint(
    *,
    base_url: str,
    endpoint: dict[str, Any],
    required_fields: list[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    method = str(endpoint.get("method") or "GET").upper()
    path = str(endpoint.get("path") or "")
    url = urljoin(f"{base_url}/", path.lstrip("/"))
    try:
        payload = _request_json(
            method=method,
            url=url,
            payload=_request_payload(endpoint=endpoint, method=method),
            timeout_seconds=timeout_seconds,
        )
        missing_fields = [
            field
            for field in required_fields
            if field not in payload
        ]
        if missing_fields:
            return {
                "method": method,
                "path": path,
                "url": url,
                "status": "failed",
                "reason": f"missing envelope fields: {', '.join(missing_fields)}",
            }
        return {
            "method": method,
            "path": path,
            "url": url,
            "status": "passed",
            "reason": "",
        }
    except Exception as exc:
        return {
            "method": method,
            "path": path,
            "url": url,
            "status": "failed",
            "reason": str(exc),
        }


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            response_payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    if not isinstance(response_payload, dict):
        raise ValueError("response must be a JSON object")
    return response_payload


def _request_payload(*, endpoint: dict[str, Any], method: str) -> dict[str, Any] | None:
    if method != "POST":
        return None
    payload = endpoint.get("conformance_payload")
    if isinstance(payload, dict):
        return payload
    return {"dry_run": True, "events": []}


def _required_envelope_fields(contract: dict[str, Any]) -> list[str]:
    envelope = contract.get("runtime", {}).get("response_envelope", {})
    fields = envelope.get("required_fields", [])
    return [str(field) for field in fields if str(field)]


def _status(endpoint_results: list[dict[str, Any]]) -> str:
    if endpoint_results and all(result["status"] == "passed" for result in endpoint_results):
        return "completed"
    if any(result["status"] == "passed" for result in endpoint_results):
        return "partial"
    return "failed"


def _default_output_dir() -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / "narrative_service_conformance" / timestamp


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "narrative_service_conformance_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "narrative_service_conformance_report.md").write_text(
        _markdown_report(report["result"]),
        encoding="utf-8",
    )


def _markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Narrative Service Conformance Probe",
        "",
        f"- Status: `{result['status']}`",
        f"- Base URL: `{result['base_url']}`",
        f"- Contract Version: `{result['contract_version']}`",
        "",
        "## Endpoints",
        "",
    ]
    if result["endpoint_results"]:
        lines.extend(
            f"- `{item['method']} {item['path']}`: `{item['status']}` {item['reason']}"
            for item in result["endpoint_results"]
        )
    else:
        lines.append("- None")
    lines.extend(["", "## Failures", ""])
    if result["failures"]:
        lines.extend(
            f"- `{item['capability']}`: {item['reason']}"
            for item in result["failures"]
        )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
