from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.providers.narrative_service import build_narrative_data_provider  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Narrative Service provider smoke check."
    )
    parser.add_argument("--base-url", default=os.environ.get("NARRATIVE_SERVICE_URL", ""))
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    provider = build_narrative_data_provider(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
    )
    snapshot = provider.get_snapshot()
    result = _result(snapshot=snapshot, configured_base_url=args.base_url.strip())
    report = {
        "version": "narrative-service-provider-smoke-v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "result": result,
    }
    _write_outputs(output_dir=output_dir, report=report)
    print(
        json.dumps(
            {
                "json": str(output_dir / "narrative_service_provider_smoke.json"),
                "markdown": str(output_dir / "narrative_service_provider_smoke.md"),
                "status": result["status"],
                "source": result["source"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["status"] in {"completed", "partial"} else 1


def _result(*, snapshot: dict[str, Any], configured_base_url: str) -> dict[str, Any]:
    warnings = _list(snapshot.get("warnings"))
    diagnostics = _mapping(snapshot.get("diagnostics"))
    registry = _mapping(snapshot.get("narrative_registry"))
    mappings = _list(snapshot.get("stock_narrative_mappings"))
    source = str(snapshot.get("source") or "")
    return {
        "capability": "narrative_service_provider",
        "status": _status(source=source, registry=registry, mappings=mappings),
        "configured_base_url": configured_base_url,
        "source": source,
        "provider": str(snapshot.get("provider") or ""),
        "provider_version": str(snapshot.get("provider_version") or ""),
        "registry_count": len(_list(registry.get("narratives"))),
        "mapping_count": len(mappings),
        "warning_count": len(warnings),
        "warning_codes": [
            str(item.get("code") or "")
            for item in warnings
            if isinstance(item, dict) and item.get("code")
        ],
        "diagnostics": diagnostics,
    }


def _status(
    *,
    source: str,
    registry: dict[str, Any],
    mappings: list[dict[str, Any]],
) -> str:
    if source and registry and mappings:
        return "completed"
    if source and registry:
        return "partial"
    return "failed"


def _default_output_dir() -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace(":", "")
    return DEFAULT_OUTPUT_DIR / "narrative_service_provider_smoke" / timestamp


def _write_outputs(*, output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "narrative_service_provider_smoke.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "narrative_service_provider_smoke.md").write_text(
        _markdown_report(report["result"]),
        encoding="utf-8",
    )


def _markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Narrative Service Provider Smoke",
        "",
        f"- Status: `{result['status']}`",
        f"- Source: `{result['source']}`",
        f"- Provider: `{result['provider']}`",
        f"- Registry Count: `{result['registry_count']}`",
        f"- Mapping Count: `{result['mapping_count']}`",
        f"- Warning Count: `{result['warning_count']}`",
        "",
    ]
    return "\n".join(lines)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())

