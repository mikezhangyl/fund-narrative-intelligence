from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

TEST_RUN_ROOT = Path(".ecc/test-runs")

REQUIRED_FILES = (
    "run-state.json",
    "intake.md",
    "observations/system-map.md",
    "observations/flows.md",
    "observations/api-observations.json",
    "defects.md",
    "automation-candidates.md",
    "report.md",
    "memory-candidates.md",
    "evidence/index.md",
)

ALLOWED_PHASES = {
    "manual_recon",
    "manual_flow_verification",
    "automation_candidate_selection",
    "smoke_automation",
    "memory_distillation",
    "closed",
}


@dataclass(frozen=True)
class QaRunResult:
    status: str
    run_dir: str
    findings: list[str]


def init_test_run(run_id: str, root: Path = TEST_RUN_ROOT) -> QaRunResult:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    for child in (
        "observations",
        "evidence",
        "evidence/screenshots",
        "evidence/videos",
        "evidence/traces",
        "evidence/har",
    ):
        (run_dir / child).mkdir()

    _write_json(
        run_dir / "run-state.json",
        {
            "run_id": run_id,
            "phase": "manual_recon",
            "created_at": date.today().isoformat(),
            "system_card_updated": False,
            "critical_flows_discovered": 0,
            "critical_flows_verified": 0,
            "automation_ready": False,
            "memory_distilled": False,
            "next_recommended_phase": "manual_recon",
        },
    )
    _write_text(run_dir / "intake.md", "# Intake\n\n## Goal\n\n## Environment\n\n## Access\n\n## Constraints\n")
    _write_text(run_dir / "observations" / "system-map.md", "# System Map\n")
    _write_text(run_dir / "observations" / "flows.md", "# Flows\n")
    _write_json(run_dir / "observations" / "api-observations.json", {"observed_apis": []})
    _write_text(run_dir / "defects.md", "# Defects\n")
    _write_text(run_dir / "automation-candidates.md", "# Automation Candidates\n")
    _write_text(run_dir / "report.md", "# Test Report\n")
    _write_text(run_dir / "memory-candidates.md", "# Memory Candidates\n")
    _write_text(run_dir / "evidence" / "index.md", "# Evidence Index\n")
    return QaRunResult(status="created", run_dir=str(run_dir), findings=[])


def validate_test_run(run_id: str, root: Path = TEST_RUN_ROOT) -> QaRunResult:
    run_dir = root / run_id
    findings: list[str] = []
    if not run_dir.exists():
        return QaRunResult(status="failed", run_dir=str(run_dir), findings=[f"Run directory not found: {run_dir}"])

    for relative in REQUIRED_FILES:
        if not (run_dir / relative).is_file():
            findings.append(f"Missing required file: {relative}")

    state = _read_json(run_dir / "run-state.json", findings)
    if isinstance(state, dict):
        phase = state.get("phase")
        if phase not in ALLOWED_PHASES:
            findings.append(f"run-state.json phase is invalid: {phase}")
        for field in (
            "run_id",
            "created_at",
            "system_card_updated",
            "critical_flows_discovered",
            "critical_flows_verified",
            "automation_ready",
            "memory_distilled",
            "next_recommended_phase",
        ):
            if field not in state:
                findings.append(f"run-state.json missing required field: {field}")
        if state.get("run_id") != run_id:
            findings.append("run-state.json run_id must match the directory name")
        discovered = state.get("critical_flows_discovered")
        verified = state.get("critical_flows_verified")
        automation_ready = state.get("automation_ready")
        memory_distilled = state.get("memory_distilled")
        if not isinstance(discovered, int) or discovered < 0:
            findings.append("critical_flows_discovered must be a non-negative integer")
        if not isinstance(verified, int) or verified < 0:
            findings.append("critical_flows_verified must be a non-negative integer")
        if isinstance(discovered, int) and isinstance(verified, int) and verified > discovered:
            findings.append("critical_flows_verified cannot exceed critical_flows_discovered")
        if automation_ready is True and verified == 0:
            findings.append("automation_ready true requires at least one verified critical flow")
        if phase in {"automation_candidate_selection", "smoke_automation"} and verified == 0:
            findings.append(f"{phase} requires at least one verified critical flow")
        if phase == "closed" and memory_distilled is not True:
            findings.append("closed phase requires memory_distilled true")

    api_observations = _read_json(run_dir / "observations" / "api-observations.json", findings)
    if isinstance(api_observations, dict) and not isinstance(api_observations.get("observed_apis"), list):
        findings.append("api-observations.json observed_apis must be a list")

    return QaRunResult(status="passed" if not findings else "failed", run_dir=str(run_dir), findings=findings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and validate QA ECC test runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--run-id", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--run-id", required=True)

    args = parser.parse_args()
    if args.command == "init":
        result = init_test_run(args.run_id)
    elif args.command == "validate":
        result = validate_test_run(args.run_id)
    else:
        raise ValueError(f"Unsupported command: {args.command}")
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status in {"created", "passed"} else 1


def _read_json(path: Path, findings: list[str]) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        findings.append(f"Invalid JSON in {path}: {error}")
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
