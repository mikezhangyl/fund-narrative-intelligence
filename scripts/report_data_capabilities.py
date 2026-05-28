from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data.capabilities import (  # noqa: E402
    DEFAULT_CAPABILITY_CONFIG_PATH,
    DataCapabilityRegistry,
    load_data_capability_registry,
)

OutputFormat = Literal["markdown", "json"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the market-data capability registry."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CAPABILITY_CONFIG_PATH,
        help="Path to data_capabilities.yaml.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        dest="output_format",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    registry = load_data_capability_registry(args.config)
    report = build_report(registry, output_format=args.output_format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


def build_report(
    registry: DataCapabilityRegistry,
    *,
    output_format: OutputFormat,
) -> str:
    if output_format == "json":
        return json.dumps(registry.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    if output_format != "markdown":
        raise ValueError(f"unsupported data capability report format: {output_format}")
    return _markdown_report(registry)


def _markdown_report(registry: DataCapabilityRegistry) -> str:
    summary = registry.summary()
    lines = [
        "# Data Capability Registry",
        "",
        f"- Version: `{registry.version}`",
        f"- Updated at: `{registry.updated_at}`",
        f"- Dataset count: `{summary['dataset_count']}`",
        f"- Analysis capability count: `{summary['analysis_capability_count']}`",
        "",
        "## Gateway Ownership Boundary",
        "",
        *_ownership_policy_lines(registry.ownership_policy),
        "",
        "## Dataset Status",
        "",
    ]
    lines.extend(_counts_markdown(summary["dataset_status_counts"]))
    lines.extend(
        [
            "",
            "## Gateway Mode",
            "",
        ]
    )
    lines.extend(_counts_markdown(summary["gateway_mode_counts"]))
    lines.extend(
        [
            "",
            "## Datasets",
            "",
            "| Dataset | Status | Difficulty | Gateway | Primary Source | Validation Probe | Use Cases |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for dataset in registry.datasets.values():
        lines.append(
            "| {dataset_id} | {status} | {difficulty} | {gateway} | {source} | {probe} | {use_cases} |".format(
                dataset_id=dataset.dataset_id,
                status=dataset.current_status,
                difficulty=dataset.acquisition_difficulty,
                gateway=dataset.gateway_mode,
                source=(
                    f"{dataset.primary_source.provider}.{dataset.primary_source.endpoint}"
                ),
                probe=dataset.validation_probe_capability or "",
                use_cases=", ".join(dataset.analysis_use_cases),
            )
        )
    lines.extend(
        [
            "",
            "## Analysis Capabilities",
            "",
            "| Capability | Status | Complexity | Can Run | Blockers | Warnings | Required Datasets | Metrics |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for capability in registry.analysis_capabilities.values():
        readiness = registry.analysis_readiness(capability.capability_id)
        lines.append(
            "| {capability_id} | {status} | {complexity} | {can_run} | {blockers} | {warnings} | {datasets} | {metrics} |".format(
                capability_id=capability.capability_id,
                status=capability.implementation_status,
                complexity=capability.complexity,
                can_run=readiness["can_run"],
                blockers=", ".join(readiness["blockers"]),
                warnings=", ".join(readiness["warnings"]),
                datasets=", ".join(capability.required_datasets),
                metrics=", ".join(capability.output_metrics),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _counts_markdown(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- None"]
    return [f"- `{key}`: `{value}`" for key, value in sorted(counts.items())]


def _ownership_policy_lines(policy: dict[str, object]) -> list[str]:
    if not policy:
        return ["- Not declared"]
    return [
        f"- External source expansion owner: `{policy.get('external_source_expansion_owner', '')}`",
        f"- FNI role: `{policy.get('fni_role', '')}`",
        f"- Direct external source rule: `{policy.get('direct_external_source_rule', '')}`",
        f"- Change request location: `{policy.get('change_request_location', '')}`",
        f"- Report disclosure required: `{policy.get('report_disclosure_required', '')}`",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
