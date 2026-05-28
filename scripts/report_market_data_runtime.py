from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data.runtime_config import inspect_market_data_runtime  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect current V0 market-data runtime source configuration."
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
    )
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(config_path=args.config, output_format=args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


def build_report(*, config_path: Path | None = None, output_format: str) -> str:
    runtime = inspect_market_data_runtime(
        config_path=config_path
        if config_path is not None
        else PROJECT_ROOT / "config" / "data_sources.yaml"
    ).to_dict()
    if output_format == "json":
        return json.dumps(runtime, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output_format == "markdown":
        return _markdown_report(runtime)
    raise ValueError(f"unsupported output format: {output_format}")


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Market Data Runtime Configuration",
        "",
        f"- Version: `{report['version']}`",
        f"- Generated At: `{report['generated_at']}`",
        f"- Config Path: `{report['config_path']}`",
        f"- Cache Dir: `{report['default_cache_dir']}`",
        f"- Cache Dir Exists: `{report['default_cache_dir_exists']}`",
        f"- Request Log Path: `{report['request_log_path']}`",
        f"- Request Log Exists: `{report['request_log_path_exists']}`",
        f"- Gateway Configured: `{report['gateway']['base_url_configured']}`",
        f"- Gateway URL Kind: `{report['gateway']['base_url_kind']}`",
        "",
        "## Providers",
        "",
        "| Provider | Enabled | URL Kind | Gateway | Token | Endpoints | Pacing | Retries |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for provider in report["providers"]:
        token = provider.get("token") or {}
        token_status = (
            f"{token.get('source', 'n/a')}"
            if token.get("configured")
            else "absent"
        )
        lines.append(
            "| "
            f"{provider['provider']} | "
            f"{provider['enabled']} | "
            f"{provider.get('api_url_kind') or 'n/a'} | "
            f"{provider.get('gateway_configured')} | "
            f"{token_status} | "
            f"{len(provider['endpoints'])} | "
            f"{provider.get('pacing_seconds') or ''} | "
            f"{provider.get('retry_attempts') if provider.get('retry_attempts') is not None else ''} |"
        )
    excluded = report.get("excluded_v0", [])
    if excluded:
        lines.extend(["", "## Explicitly Excluded From V0", ""])
        lines.extend(f"- `{item}`" for item in excluded)
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
