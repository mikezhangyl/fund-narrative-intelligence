from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import main as pipeline_main  # noqa: E402

FUND_CODE = "000001"
EXPECTED_ARTIFACTS = {
    "raw": f"fund_{FUND_CODE}_raw.json",
    "scoring": f"fund_{FUND_CODE}_scoring.json",
    "review_queue": f"fund_{FUND_CODE}_review_queue.json",
    "source_table": f"fund_{FUND_CODE}_source_table.json",
    "signal_trace": f"fund_{FUND_CODE}_signal_trace.json",
    "manifest": f"fund_{FUND_CODE}_manifest.json",
    "markdown": f"fund_{FUND_CODE}_report.md",
    "html": f"fund_{FUND_CODE}_report.html",
    "workspace_snapshot": f"fund_{FUND_CODE}_workspace_snapshot.json",
}


class AcceptanceError(RuntimeError):
    """Raised when the V1 acceptance contract is not satisfied."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the V1 acceptance flow and validate generated artifacts."
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. If omitted, a temporary directory is used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            _run_acceptance(output_dir)
            _print_success(output_dir)
            return 0

        with tempfile.TemporaryDirectory(prefix="fni-v1-acceptance-") as tmp:
            output_dir = Path(tmp)
            _run_acceptance(output_dir)
            _print_success(output_dir)
            return 0
    except AcceptanceError as exc:
        print("V1 acceptance failed:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


def _run_acceptance(output_dir: Path) -> None:
    _run_cli(["--fund-code", FUND_CODE, "--output-dir", str(output_dir)])
    workspace_snapshot_path = output_dir / EXPECTED_ARTIFACTS["workspace_snapshot"]
    if workspace_snapshot_path.exists():
        workspace_snapshot_path.unlink()
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    _run_cli(["--build-workspace-snapshot", str(output_dir)])
    _run_cli(["--validate-artifact-contracts", str(output_dir)])
    _run_cli(["--validate-workspace-snapshot", str(workspace_snapshot_path)])
    validate_acceptance_outputs(output_dir)


def validate_acceptance_outputs(output_dir: Path) -> None:
    artifacts = {
        key: output_dir / filename for key, filename in EXPECTED_ARTIFACTS.items()
    }
    for key, path in artifacts.items():
        if key == "workspace_snapshot":
            continue
        if not path.is_file():
            raise AcceptanceError(f"missing {key} artifact: {path}")

    raw = _read_json(artifacts["raw"])
    scoring = _read_json(artifacts["scoring"])
    manifest = _read_json(artifacts["manifest"])
    review_queue = _read_json(artifacts["review_queue"])
    source_table = _read_json(artifacts["source_table"])
    signal_trace = _read_json(artifacts["signal_trace"])
    markdown = artifacts["markdown"].read_text(encoding="utf-8")
    html = artifacts["html"].read_text(encoding="utf-8")

    _require(raw.get("metadata", {}).get("fund_code") == FUND_CODE, "raw fund_code mismatch")
    _require(
        raw.get("metadata", {}).get("data_quality") == "mock",
        "raw data_quality must be mock for V1 acceptance",
    )
    _require(
        _mock_source_url(
            raw.get("fund", {}).get("provider_metadata", {}).get("source_url")
        ),
        "raw fund provider source_url must disclose mock fixture",
    )

    foundation = scoring.get("provider_foundation", {})
    _require(
        scoring.get("metadata", {}).get("data_quality") == "mock",
        "scoring data_quality must be mock for V1 acceptance",
    )
    _require(
        foundation.get("effective_data_quality") == "mock",
        "provider foundation effective_data_quality must be mock",
    )
    _require(
        _mock_source_url(
            foundation.get("layers", {}).get("holdings", {}).get("source_url")
        ),
        "provider foundation holdings source_url must disclose mock fixture",
    )

    _require(
        manifest.get("version") == "pipeline-artifact-manifest-v1",
        "manifest version mismatch",
    )
    _require(manifest.get("fund_code") == FUND_CODE, "manifest fund_code mismatch")
    _require(manifest.get("web_ready") is True, "manifest must be web_ready")
    manifest_artifacts = manifest.get("artifacts", {})
    for key, filename in EXPECTED_ARTIFACTS.items():
        if key in {"manifest", "workspace_snapshot"}:
            continue
        artifact = manifest_artifacts.get(key)
        _require(isinstance(artifact, dict), f"manifest missing artifact: {key}")
        _require(
            artifact.get("path") == filename,
            f"manifest artifact {key} path mismatch",
        )

    queue = review_queue.get("candidate_review_queue", {})
    _require(
        queue.get("version") == "candidate-review-queue-v1",
        "review queue version mismatch",
    )
    _require(
        source_table.get("version") == "source-table-v1",
        "source table version mismatch",
    )
    _require(
        source_table.get("fund_code") == FUND_CODE,
        "source table fund_code mismatch",
    )
    _require(
        source_table.get("provider_foundation") == foundation,
        "source table provider foundation mismatch",
    )
    _require(
        signal_trace.get("version") == "signal-trace-v1",
        "signal trace version mismatch",
    )
    _require(signal_trace.get("fund_code") == FUND_CODE, "signal trace fund_code mismatch")
    _require(
        signal_trace.get("provider_foundation") == foundation,
        "signal trace provider foundation mismatch",
    )
    _require(
        any(
            _mock_source_url(signal.get("source_url"))
            for narrative in signal_trace.get("narratives", [])
            if isinstance(narrative, dict)
            for dimension in narrative.get("dimensions", [])
            if isinstance(dimension, dict)
            for signal in dimension.get("signals", [])
            if isinstance(signal, dict)
        ),
        "signal trace must expose mock source URLs for mock baseline",
    )
    _require(
        "Data Source Notice" in markdown and "Mock 数据" in markdown,
        "Markdown report must disclose mock data",
    )
    _require(
        "Data Source Notice" in html and "Mock 数据" in html,
        "HTML report must disclose mock data",
    )
    _require(
        "mock://fixtures/fund_000001.json" in markdown,
        "Markdown report must show mock fixture source URL",
    )
    _require(
        "mock://fixtures/fund_000001.json" in html,
        "HTML report must show mock fixture source URL",
    )
    if not artifacts["workspace_snapshot"].is_file():
        raise AcceptanceError(
            f"missing workspace_snapshot artifact: {artifacts['workspace_snapshot']}"
        )
    workspace_snapshot = _read_json(artifacts["workspace_snapshot"])
    _require(
        workspace_snapshot.get("version") == "workspace-snapshot-v1",
        "workspace snapshot version mismatch",
    )
    notice = workspace_snapshot.get("data_source_notice", {})
    _require(
        notice.get("display_required") is True,
        "workspace snapshot must require data source notice display",
    )
    _require(
        notice.get("severity") == "mock",
        "workspace snapshot data source notice must be mock severity",
    )
    _require(
        notice.get("mock_layer_count", 0) > 0,
        "workspace snapshot data source notice must count mock layers",
    )
    _require(
        any(
            _mock_source_url(layer.get("source_url"))
            for layer in notice.get("layers_requiring_disclosure", [])
            if isinstance(layer, dict)
        ),
        "workspace snapshot data source notice must expose mock source URLs",
    )
    data_layers = workspace_snapshot.get("data_layers", {})
    _require(
        data_layers.get("version") == "workspace-data-layers-v1",
        "workspace snapshot data_layers version mismatch",
    )
    data_layer_rows = data_layers.get("layers", [])
    _require(
        isinstance(data_layer_rows, list) and data_layer_rows,
        "workspace snapshot data_layers must include layer rows",
    )
    _require(
        any(
            layer.get("is_mock") is True and _mock_source_url(layer.get("source_url"))
            for layer in data_layer_rows
            if isinstance(layer, dict)
        ),
        "workspace snapshot data_layers must expose mock source URLs",
    )


def _run_cli(args: list[str]) -> None:
    exit_code = pipeline_main.main(args)
    if exit_code != 0:
        raise AcceptanceError(
            f"command failed with exit code {exit_code}: python -m src.main {' '.join(args)}"
        )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AcceptanceError(f"{path} must contain a JSON object")
    return payload


def _mock_source_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("mock://fixtures/")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def _print_success(output_dir: Path) -> None:
    print("V1 acceptance passed:")
    print(output_dir)
    for key in (
        "raw",
        "scoring",
        "review_queue",
        "source_table",
        "signal_trace",
        "manifest",
        "markdown",
        "html",
        "workspace_snapshot",
    ):
        print(EXPECTED_ARTIFACTS[key])


if __name__ == "__main__":
    raise SystemExit(main())
