from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskRunInitResult:
    status: str
    run_dir: str


@dataclass(frozen=True)
class TaskRunValidationResult:
    status: str
    run_dir: str
    findings: list[str]


REQUIRED_STATE_FIELDS = {
    "task_run_id",
    "task_state",
    "review_cycle",
    "branch",
    "worktree",
    "base_commit",
    "head_commit",
    "merge_base",
    "quality_reviewed_commit",
    "reviewed_snapshot_type",
    "working_tree_dirty",
    "task_type",
    "task_agent_required",
    "quality_agent_required",
    "final_decision",
    "review_outcome",
    "owning_task_agent",
    "active_agent",
    "active_agent_role",
    "child_agents_allowed",
    "same_task_role_agents_allowed",
    "quality_agent_allowed_after_state",
}

ALLOWED_STATES = {
    "planned",
    "task_agent_active",
    "ready_for_quality",
    "quality_agent_active",
    "needs_task_fix",
    "blocked",
    "passed",
    "failed",
    "closed_keep",
    "closed_merge",
    "closed_pr",
    "closed_discard",
}

ALLOWED_ACTIVE_AGENT_ROLES = {None, "implementation", "quality"}
ALLOWED_SNAPSHOT_TYPES = {None, "committed", "working_tree"}
ALLOWED_TASK_TYPES = {
    "implementation",
    "review-only",
    "workflow-change",
    "project-bootstrap",
    "skill-review-fix",
    "helper-implementation",
    "workflow-retention-policy",
}
FINAL_DECISIONS = {"keep", "merge", "pr", "discard"}
CLOSED_STATE_DECISIONS = {
    "closed_keep": "keep",
    "closed_merge": "merge",
    "closed_pr": "pr",
    "closed_discard": "discard",
}
QUALITY_STATUSES = {"passed", "needs_fix", "failed", "blocked"}
QUALITY_SUCCESS_TASK_STATES = {"passed", "closed_keep", "closed_merge", "closed_pr"}
QUALITY_CLOSED_TASK_STATES = {"closed_keep", "closed_merge", "closed_pr", "closed_discard"}
QUALITY_GATE_TASK_STATES = QUALITY_SUCCESS_TASK_STATES | {"failed", "closed_discard"}
HEX_DIGITS = set("0123456789abcdef")

ROOT_REQUIRED_FILES = (
    "run-state.json",
    "task-brief.md",
    "artifacts/generated-files-manifest.json",
)

QUALITY_REQUIRED_FILES = (
    "quality-agent/findings.json",
    "quality-agent/review-state.json",
)

TASK_REQUIRED_FILES = (
    "task-handoff.md",
    "changed-files.txt",
)

TASK_HANDOFF_SECTIONS = (
    "Goal",
    "Files Changed",
    "Implementation Summary",
    "Commands Run",
    "Test Results",
    "Known Risks And Assumptions",
    "Suggested Quality Checks",
)

FINDINGS_REQUIRED_FIELDS = {
    "status",
    "findings",
    "residual_risks",
}

REVIEW_STATE_REQUIRED_FIELDS = {
    "review_id",
    "status",
    "reviewed_at",
    "reviewed_snapshot_type",
    "quality_reviewed_commit",
    "working_tree_dirty",
    "findings_count",
    "unresolved_findings_count",
    "fix_required_before_next_phase",
}


def init_run_directory(
    *,
    run_dir: Path,
    branch: str,
    worktree: str,
    base_commit: str,
    head_commit: str,
    merge_base: str,
    task_type: str,
    task_agent_required: bool = True,
    quality_agent_required: bool = True,
) -> TaskRunInitResult:
    run_dir.mkdir(parents=True, exist_ok=False)
    for child in (
        "task-agent",
        "quality-agent",
        "artifacts",
        "artifacts/screenshots",
        "artifacts/reports",
        "artifacts/logs",
        "decisions",
    ):
        (run_dir / child).mkdir()

    state = {
        "task_run_id": run_dir.name,
        "task_state": "planned",
        "review_cycle": 0,
        "branch": branch,
        "worktree": worktree,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "merge_base": merge_base,
        "quality_reviewed_commit": None,
        "reviewed_snapshot_type": None,
        "working_tree_dirty": False,
        "task_type": task_type,
        "task_agent_required": task_agent_required,
        "quality_agent_required": quality_agent_required,
        "final_decision": None,
        "review_outcome": None,
        "owning_task_agent": None,
        "active_agent": None,
        "active_agent_role": None,
        "child_agents_allowed": False,
        "same_task_role_agents_allowed": False,
        "quality_agent_allowed_after_state": "ready_for_quality",
    }
    _write_json(run_dir / "run-state.json", state)
    (run_dir / "task-brief.md").write_text("# Task Brief\n", encoding="utf-8")
    _write_json(run_dir / "artifacts" / "generated-files-manifest.json", {"generated_artifacts": []})
    return TaskRunInitResult(status="created", run_dir=str(run_dir))


def validate_run_directory(
    run_dir: Path,
    *,
    require_quality_artifacts: bool = False,
    require_task_artifacts: bool = False,
) -> TaskRunValidationResult:
    findings: list[str] = []
    if not run_dir.exists():
        return TaskRunValidationResult(status="failed", run_dir=str(run_dir), findings=[f"Run directory not found: {run_dir}"])

    for relative_path in ROOT_REQUIRED_FILES:
        _require_file(run_dir, relative_path, findings)
    if require_quality_artifacts:
        for relative_path in QUALITY_REQUIRED_FILES:
            _require_file(run_dir, relative_path, findings)
    if require_task_artifacts:
        for relative_path in TASK_REQUIRED_FILES:
            _require_file(run_dir, relative_path, findings)

    state = _read_json(run_dir / "run-state.json", findings)
    quality_artifacts_validated = False
    if isinstance(state, dict):
        _validate_state(run_dir, state, findings)
        if _state_requires_quality_gate(state):
            _validate_quality_artifacts(run_dir, findings, state=state)
            quality_artifacts_validated = True

    manifest = _read_json(run_dir / "artifacts" / "generated-files-manifest.json", findings)
    if isinstance(manifest, dict):
        _validate_manifest(run_dir, manifest, findings)

    if require_task_artifacts:
        _validate_task_handoff(run_dir / "task-handoff.md", findings)
    if require_quality_artifacts and not quality_artifacts_validated:
        _validate_quality_artifacts(run_dir, findings, state=state if isinstance(state, dict) else None)

    status = "passed" if not findings else "failed"
    return TaskRunValidationResult(status=status, run_dir=str(run_dir), findings=findings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and validate ECC task-agent run directories.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--run-dir", type=Path, required=True)
    init_parser.add_argument("--branch", required=True)
    init_parser.add_argument("--worktree", required=True)
    init_parser.add_argument("--base-commit", required=True)
    init_parser.add_argument("--head-commit", required=True)
    init_parser.add_argument("--merge-base", required=True)
    init_parser.add_argument("--task-type", required=True)
    init_parser.add_argument("--review-only", action="store_true")
    quality_group = init_parser.add_mutually_exclusive_group()
    quality_group.add_argument("--quality-agent-required", dest="quality_agent_required", action="store_true")
    quality_group.add_argument(
        "--no-quality-agent-required",
        "--no-quality-agent",
        dest="quality_agent_required",
        action="store_false",
    )
    init_parser.set_defaults(quality_agent_required=None)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--run-dir", type=Path, required=True)
    validate_parser.add_argument("--require-quality-artifacts", action="store_true")
    validate_parser.add_argument("--require-task-artifacts", action="store_true")

    args = parser.parse_args()
    if args.command == "init":
        quality_agent_required = True if args.quality_agent_required is None else args.quality_agent_required
        result = init_run_directory(
            run_dir=args.run_dir,
            branch=args.branch,
            worktree=args.worktree,
            base_commit=args.base_commit,
            head_commit=args.head_commit,
            merge_base=args.merge_base,
            task_type=args.task_type,
            task_agent_required=not args.review_only,
            quality_agent_required=quality_agent_required,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate":
        result = validate_run_directory(
            args.run_dir,
            require_quality_artifacts=args.require_quality_artifacts,
            require_task_artifacts=args.require_task_artifacts,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0 if result.status == "passed" else 1
    raise ValueError(f"Unsupported command: {args.command}")


def _validate_state(run_dir: Path, state: dict[str, Any], findings: list[str]) -> None:
    missing = sorted(REQUIRED_STATE_FIELDS - set(state))
    for field in missing:
        findings.append(f"run-state.json missing required field: {field}")

    if state.get("task_run_id") != run_dir.name:
        findings.append("run-state.json task_run_id must match the run directory name")
    if state.get("task_state") not in ALLOWED_STATES:
        findings.append(f"run-state.json task_state is invalid: {state.get('task_state')}")
    if state.get("task_type") not in ALLOWED_TASK_TYPES:
        findings.append(f"run-state.json task_type is invalid: {state.get('task_type')}")
    if not isinstance(state.get("task_agent_required"), bool):
        findings.append("run-state.json task_agent_required must be boolean")
    if not isinstance(state.get("quality_agent_required"), bool):
        findings.append("run-state.json quality_agent_required must be boolean")
    if state.get("child_agents_allowed") is not False:
        findings.append("run-state.json child_agents_allowed must be false")
    if state.get("same_task_role_agents_allowed") is not False:
        findings.append("run-state.json same_task_role_agents_allowed must be false")
    if state.get("quality_agent_allowed_after_state") != "ready_for_quality":
        findings.append("run-state.json quality_agent_allowed_after_state must be ready_for_quality")
    if state.get("active_agent_role") not in ALLOWED_ACTIVE_AGENT_ROLES:
        findings.append(f"run-state.json active_agent_role is invalid: {state.get('active_agent_role')}")
    if state.get("active_agent") is None and state.get("active_agent_role") is not None:
        findings.append("run-state.json active_agent_role requires active_agent")
    if state.get("task_state") == "quality_agent_active":
        if state.get("active_agent") is None or state.get("active_agent_role") != "quality":
            findings.append("quality_agent_active requires active_agent_role quality and a non-null active_agent")
    elif state.get("task_state") == "task_agent_active":
        if state.get("active_agent") is None or state.get("active_agent_role") != "implementation":
            findings.append("task_agent_active requires active_agent_role implementation and a non-null active_agent")
    elif state.get("active_agent") is not None or state.get("active_agent_role") is not None:
        findings.append("non-active task states require active_agent and active_agent_role to be null")
    if state.get("reviewed_snapshot_type") not in ALLOWED_SNAPSHOT_TYPES:
        findings.append(f"run-state.json reviewed_snapshot_type is invalid: {state.get('reviewed_snapshot_type')}")
    if state.get("reviewed_snapshot_type") == "working_tree" and state.get("working_tree_dirty") is not True:
        findings.append("run-state.json working_tree snapshot requires working_tree_dirty true")
    if state.get("reviewed_snapshot_type") != "working_tree" and state.get("working_tree_dirty") is True:
        findings.append("run-state.json working_tree_dirty true requires reviewed_snapshot_type working_tree")
    if state.get("reviewed_snapshot_type") == "working_tree" and not _manifest_has_artifacts(run_dir):
        findings.append("working_tree snapshot requires manifest artifacts")
    if _state_requires_quality_gate(state):
        if not _has_quality_artifacts(run_dir):
            findings.append("quality_agent_required true requires quality artifacts before passed or closed states")
        if state.get("quality_reviewed_commit") is None and state.get("reviewed_snapshot_type") != "working_tree":
            findings.append("quality_agent_required true requires quality_reviewed_commit or working_tree review snapshot")
    final_decision = state.get("final_decision")
    task_state = state.get("task_state")
    if task_state in CLOSED_STATE_DECISIONS:
        expected = CLOSED_STATE_DECISIONS[task_state]
        if final_decision != expected:
            findings.append(f"{task_state} requires final_decision {expected}")
    elif final_decision in FINAL_DECISIONS:
        findings.append("final_decision keep/merge/pr/discard is only allowed with closed_* states")


def _validate_manifest(run_dir: Path, manifest: dict[str, Any], findings: list[str]) -> None:
    artifacts = manifest.get("generated_artifacts")
    if not isinstance(artifacts, list):
        findings.append("generated-files-manifest.json generated_artifacts must be a list")
        return
    project_root = _project_root_for_run(run_dir)
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            findings.append(f"generated-files-manifest.json artifact {index} must be an object")
            continue
        for field in ("type", "path", "owned_by_task", "reviewed_snapshot_type", "summary"):
            if field not in artifact:
                findings.append(f"generated-files-manifest.json artifact {index} missing required field: {field}")
        if "owned_by_task" in artifact and not isinstance(artifact.get("owned_by_task"), bool):
            findings.append(f"generated-files-manifest.json artifact {index} owned_by_task must be boolean")
        if "path" in artifact and not isinstance(artifact.get("path"), str):
            findings.append(f"generated-files-manifest.json artifact {index} path must be a string")
        if artifact.get("reviewed_snapshot_type") not in ALLOWED_SNAPSHOT_TYPES - {None}:
            findings.append(f"generated-files-manifest.json artifact {index} reviewed_snapshot_type is invalid: {artifact.get('reviewed_snapshot_type')}")
        if artifact.get("reviewed_snapshot_type") == "working_tree":
            for field in ("checksum_sha256", "mtime_epoch", "size_bytes"):
                if field not in artifact:
                    findings.append(f"generated-files-manifest.json working_tree artifact {index} missing field: {field}")
        if artifact.get("owned_by_task") is True and isinstance(artifact.get("path"), str) and _is_local_artifact_path(artifact["path"]):
            _validate_local_manifest_artifact(index, project_root, artifact, findings)

def _validate_task_handoff(path: Path, findings: list[str]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for section in TASK_HANDOFF_SECTIONS:
        if f"## {section}" not in text:
            findings.append(f"task-handoff.md missing section: {section}")


def _validate_quality_artifacts(
    run_dir: Path,
    findings: list[str],
    *,
    state: dict[str, Any] | None = None,
) -> None:
    findings_payload = _read_json(run_dir / "quality-agent" / "findings.json", findings)
    if isinstance(findings_payload, dict):
        _validate_required_fields("quality-agent/findings.json", findings_payload, FINDINGS_REQUIRED_FIELDS, findings)
        if "findings" in findings_payload and not isinstance(findings_payload["findings"], list):
            findings.append("quality-agent/findings.json findings must be a list")
        if "residual_risks" in findings_payload and not isinstance(findings_payload["residual_risks"], list):
            findings.append("quality-agent/findings.json residual_risks must be a list")
        if "status" in findings_payload and findings_payload.get("status") not in QUALITY_STATUSES:
            findings.append(f"quality-agent/findings.json status is invalid: {findings_payload.get('status')}")

    review_state = _read_json(run_dir / "quality-agent" / "review-state.json", findings)
    if isinstance(review_state, dict):
        _validate_required_fields("quality-agent/review-state.json", review_state, REVIEW_STATE_REQUIRED_FIELDS, findings)
        if "status" in review_state and review_state.get("status") not in QUALITY_STATUSES:
            findings.append(f"quality-agent/review-state.json status is invalid: {review_state.get('status')}")
        if "reviewed_snapshot_type" in review_state and review_state.get("reviewed_snapshot_type") not in ALLOWED_SNAPSHOT_TYPES - {None}:
            findings.append(f"quality-agent/review-state.json reviewed_snapshot_type is invalid: {review_state.get('reviewed_snapshot_type')}")
        for field in ("working_tree_dirty", "fix_required_before_next_phase"):
            if field in review_state and not isinstance(review_state.get(field), bool):
                findings.append(f"quality-agent/review-state.json {field} must be boolean")
        for field in ("findings_count", "unresolved_findings_count"):
            if field in review_state and not _is_non_negative_int(review_state.get(field)):
                findings.append(f"quality-agent/review-state.json {field} must be a non-negative integer")

    if state is not None and isinstance(findings_payload, dict) and isinstance(review_state, dict):
        _validate_quality_semantics(run_dir, state, findings_payload, review_state, findings)


def _validate_required_fields(
    artifact_name: str,
    payload: dict[str, Any],
    required_fields: set[str],
    findings: list[str],
) -> None:
    missing = sorted(required_fields - set(payload))
    for field in missing:
        findings.append(f"{artifact_name} missing required field: {field}")


def _validate_quality_semantics(
    run_dir: Path,
    state: dict[str, Any],
    findings_payload: dict[str, Any],
    review_state: dict[str, Any],
    findings: list[str],
) -> None:
    task_state = state.get("task_state")
    findings_status = findings_payload.get("status")
    review_status = review_state.get("status")
    expected_review_id = state.get("task_run_id", run_dir.name)
    if review_state.get("review_id") != expected_review_id:
        findings.append("quality-agent/review-state.json review_id must match the task_run_id")
    if findings_status in QUALITY_STATUSES and review_status in QUALITY_STATUSES and findings_status != review_status:
        findings.append("quality-agent findings status and review-state status must match")
    if task_state in QUALITY_SUCCESS_TASK_STATES:
        _require_quality_status(task_state, "quality-agent/findings.json", findings_status, {"passed"}, findings)
        _require_quality_status(task_state, "quality-agent/review-state.json", review_status, {"passed"}, findings)
    elif task_state == "failed":
        _require_quality_status(task_state, "quality-agent/findings.json", findings_status, {"failed", "blocked"}, findings)
        _require_quality_status(task_state, "quality-agent/review-state.json", review_status, {"failed", "blocked"}, findings)
    elif task_state == "closed_discard":
        _require_quality_status(task_state, "quality-agent/findings.json", findings_status, {"passed", "failed", "blocked"}, findings)
        _require_quality_status(task_state, "quality-agent/review-state.json", review_status, {"passed", "failed", "blocked"}, findings)
    if review_state.get("fix_required_before_next_phase") is True and (task_state == "passed" or task_state in QUALITY_CLOSED_TASK_STATES):
        findings.append("quality-agent/review-state.json fix_required_before_next_phase true blocks passed and closed_* states")
    if state.get("quality_reviewed_commit") is not None and review_state.get("quality_reviewed_commit") != state.get("quality_reviewed_commit"):
        findings.append("quality-agent/review-state.json quality_reviewed_commit must match run-state.json")
    if state.get("reviewed_snapshot_type") is not None and review_state.get("reviewed_snapshot_type") != state.get("reviewed_snapshot_type"):
        findings.append("quality-agent/review-state.json reviewed_snapshot_type must match run-state.json")
    if isinstance(state.get("working_tree_dirty"), bool) and review_state.get("working_tree_dirty") != state.get("working_tree_dirty"):
        findings.append("quality-agent/review-state.json working_tree_dirty must match run-state.json")


def _require_quality_status(
    task_state: str,
    artifact_name: str,
    actual_status: Any,
    allowed_statuses: set[str],
    findings: list[str],
) -> None:
    if actual_status in QUALITY_STATUSES and actual_status not in allowed_statuses:
        expected = "|".join(sorted(allowed_statuses))
        findings.append(f"{artifact_name} status {actual_status} is incompatible with task_state {task_state}; expected {expected}")


def _validate_local_manifest_artifact(
    index: int,
    project_root: Path,
    artifact: dict[str, Any],
    findings: list[str],
) -> None:
    artifact_path = Path(artifact["path"])
    local_path = artifact_path if artifact_path.is_absolute() else project_root / artifact_path
    if not local_path.exists():
        findings.append(f"generated-files-manifest.json artifact {index} path does not exist: {artifact['path']}")
        return
    if not local_path.is_file():
        return
    if "checksum_sha256" in artifact:
        expected_checksum = artifact.get("checksum_sha256")
        if not _is_sha256(expected_checksum):
            findings.append(f"generated-files-manifest.json artifact {index} checksum_sha256 must be a lowercase sha256 hex string")
        else:
            actual_checksum = hashlib.sha256(local_path.read_bytes()).hexdigest()
            if actual_checksum != expected_checksum:
                findings.append(f"generated-files-manifest.json artifact {index} checksum_sha256 mismatch for {artifact['path']}")
    if "size_bytes" in artifact:
        expected_size = artifact.get("size_bytes")
        if not _is_non_negative_int(expected_size):
            findings.append(f"generated-files-manifest.json artifact {index} size_bytes must be a non-negative integer")
        elif local_path.stat().st_size != expected_size:
            findings.append(f"generated-files-manifest.json artifact {index} size_bytes mismatch for {artifact['path']}")
    if "mtime_epoch" in artifact:
        expected_mtime = artifact.get("mtime_epoch")
        if not _is_non_negative_int(expected_mtime):
            findings.append(f"generated-files-manifest.json artifact {index} mtime_epoch must be a non-negative integer")
        elif int(local_path.stat().st_mtime) != expected_mtime:
            findings.append(f"generated-files-manifest.json artifact {index} mtime_epoch mismatch for {artifact['path']}")


def _project_root_for_run(run_dir: Path) -> Path:
    resolved_run_dir = run_dir.resolve()
    if resolved_run_dir.parent.name == "runs" and resolved_run_dir.parent.parent.name == ".ecc":
        return resolved_run_dir.parent.parent.parent
    return Path.cwd()


def _is_local_artifact_path(path: str) -> bool:
    return bool(path) and "://" not in path


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in HEX_DIGITS for character in value)


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _manifest_has_artifacts(run_dir: Path) -> bool:
    try:
        manifest = json.loads((run_dir / "artifacts" / "generated-files-manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    artifacts = manifest.get("generated_artifacts")
    return isinstance(artifacts, list) and len(artifacts) > 0


def _has_quality_artifacts(run_dir: Path) -> bool:
    return all((run_dir / relative_path).is_file() for relative_path in QUALITY_REQUIRED_FILES)


def _state_requires_quality_gate(state: dict[str, Any]) -> bool:
    return state.get("quality_agent_required") is True and state.get("task_state") in QUALITY_GATE_TASK_STATES


def _require_file(run_dir: Path, relative_path: str, findings: list[str]) -> None:
    if not (run_dir / relative_path).is_file():
        findings.append(f"Missing required file: {relative_path}")


def _read_json(path: Path, findings: list[str]) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        findings.append(f"Invalid JSON in {path.name}: {error}")
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
