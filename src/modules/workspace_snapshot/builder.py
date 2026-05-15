from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.modules.snapshot_writer.writer import write_json_artifact
from src.validation import (
    validate_financial_metrics_payload,
    validate_news_evidence_payload,
    validate_pipeline_artifact_manifest_payload,
    validate_review_queue_artifact_payload,
    validate_signal_trace_artifact_payload,
    validate_source_table_artifact_payload,
    validate_valuation_snapshot_payload,
    validate_workspace_snapshot_payload,
)


def build_workspace_snapshot(
    path: Path,
    output_path: Path | None = None,
) -> Path:
    manifest_path = _resolve_manifest_path(path)
    artifact_root = manifest_path.parent
    manifest = _read_json_object(manifest_path)
    validate_pipeline_artifact_manifest_payload(manifest)
    artifacts = manifest["artifacts"]
    raw = _read_manifest_json_artifact(artifact_root, artifacts, "raw")
    scoring = _read_manifest_json_artifact(artifact_root, artifacts, "scoring")
    review_queue = _read_manifest_json_artifact(artifact_root, artifacts, "review_queue")
    source_table = _read_manifest_json_artifact(artifact_root, artifacts, "source_table")
    signal_trace = _read_manifest_json_artifact(artifact_root, artifacts, "signal_trace")
    _validate_manifest_text_artifact(artifact_root, artifacts, "markdown", "markdown")
    _validate_manifest_text_artifact(artifact_root, artifacts, "html", "html")
    validate_review_queue_artifact_payload(review_queue)
    validate_source_table_artifact_payload(source_table)
    validate_signal_trace_artifact_payload(signal_trace)
    _require_bundle_identity(
        manifest=manifest,
        raw=raw,
        scoring=scoring,
        review_queue=review_queue,
        source_table=source_table,
        signal_trace=signal_trace,
    )
    snapshot = _workspace_snapshot_payload(
        manifest=manifest,
        raw=raw,
        scoring=scoring,
        review_queue=review_queue,
        source_table=source_table,
        signal_trace=signal_trace,
        manifest_path=manifest_path,
    )
    validate_workspace_snapshot_payload(snapshot)
    destination = output_path or (
        artifact_root / f"fund_{manifest['fund_code']}_workspace_snapshot.json"
    )
    _require_output_in_artifact_root(destination, artifact_root)
    return write_json_artifact(snapshot, destination)


def _workspace_snapshot_payload(
    manifest: dict[str, Any],
    raw: dict[str, Any],
    scoring: dict[str, Any],
    review_queue: dict[str, Any],
    source_table: dict[str, Any],
    signal_trace: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    return {
        "version": "workspace-snapshot-v1",
        "fund_code": manifest["fund_code"],
        "as_of_date": manifest["as_of_date"],
        "provider_mode": manifest["provider_mode"],
        "data_quality": manifest["data_quality"],
        "web_ready": True,
        "manifest_path": manifest_path.name,
        "artifact_manifest": manifest,
        "provider_foundation": manifest["provider_foundation"],
        "data_source_notice": _data_source_notice(manifest["provider_foundation"]),
        "source_table": source_table,
        "signal_trace": signal_trace,
        "review_queue": review_queue,
        "narratives": {
            "primary": scoring.get("primary_narrative"),
            "secondary": scoring.get("secondary_narratives", []),
            "mapping_coverage": scoring.get("mapping_coverage", {}),
            "candidate_narratives": scoring.get("candidate_narratives", []),
            "excluded_mapping_candidates": scoring.get(
                "excluded_mapping_candidates", []
            ),
            "unmapped_holdings": scoring.get("unmapped_holdings", []),
        },
        "fund": raw.get("fund", {}),
        "reports": {
            "markdown": manifest["artifacts"]["markdown"],
            "html": manifest["artifacts"]["html"],
        },
        "approval_workflow": _approval_workflow(review_queue),
    }


def _data_source_notice(provider_foundation: dict[str, Any]) -> dict[str, Any]:
    layers = list(provider_foundation["layers"].values())
    mock_layers = [layer for layer in layers if layer["is_mock"]]
    unavailable_layers = [
        layer for layer in layers if layer["data_quality"] == "unavailable"
    ]
    return {
        "display_required": bool(provider_foundation["disclosure_required"]),
        "severity": _data_source_notice_severity(
            provider_foundation["effective_data_quality"],
            mock_layer_count=len(mock_layers),
            unavailable_layer_count=len(unavailable_layers),
        ),
        "effective_data_quality": provider_foundation["effective_data_quality"],
        "message": provider_foundation["disclosure_message"],
        "mock_layer_count": len(mock_layers),
        "unavailable_layer_count": len(unavailable_layers),
        "degradation_event_count": len(provider_foundation["degradation_events"]),
        "layers_requiring_disclosure": [
            _notice_layer(layer)
            for layer in layers
            if layer["is_mock"] or layer["data_quality"] != "fresh"
        ],
    }


def _data_source_notice_severity(
    effective_data_quality: str,
    *,
    mock_layer_count: int,
    unavailable_layer_count: int,
) -> str:
    if unavailable_layer_count or effective_data_quality == "unavailable":
        return "unavailable"
    if mock_layer_count or effective_data_quality == "mock":
        return "mock"
    if effective_data_quality == "partial":
        return "partial"
    return "fresh"


def _notice_layer(layer: dict[str, Any]) -> dict[str, Any]:
    return {
        "layer": layer["layer"],
        "display_name": layer["display_name"],
        "provider_name": layer["provider_name"],
        "data_quality": layer["data_quality"],
        "source_url": layer["source_url"],
        "is_mock": layer["is_mock"],
    }


def _approval_workflow(review_queue: dict[str, Any]) -> dict[str, Any]:
    candidate_queue = review_queue["candidate_review_queue"]
    items = candidate_queue["items"]
    return {
        "status": "ready_for_future_web",
        "read_only": True,
        "requires_user_approval": True,
        "preview_command": "python -m src.main --preview-review-action",
        "persist_command": "python -m src.main --persist-review-action",
        "review_queue_summary": candidate_queue["summary"],
        "available_actions": _available_actions(items),
        "review_item_count": len(items),
        "pending_review_item_count": sum(
            1 for item in items if item.get("human_review_status") == "candidate"
        ),
    }


def _available_actions(items: list[dict[str, Any]]) -> list[str]:
    actions = []
    for item in items:
        for action in item.get("available_actions", []):
            if action not in actions:
                actions.append(action)
    return actions


def _resolve_manifest_path(path: Path) -> Path:
    if path.is_file():
        return path
    if not path.is_dir():
        raise ValueError(f"{path} does not exist")
    manifests = sorted(path.glob("fund_*_manifest.json"))
    if not manifests:
        raise ValueError(f"{path} contains no fund manifest")
    if len(manifests) > 1:
        raise ValueError(f"{path} contains multiple fund manifests")
    return manifests[0]


def _read_manifest_json_artifact(
    artifact_root: Path,
    artifacts: dict[str, Any],
    artifact_key: str,
) -> dict[str, Any]:
    artifact = artifacts.get(artifact_key)
    if not isinstance(artifact, dict):
        raise ValueError(f"manifest missing artifact: {artifact_key}")
    artifact_path = artifact_root / str(artifact.get("path") or "")
    return _read_json_object(artifact_path)


def _validate_manifest_text_artifact(
    artifact_root: Path,
    artifacts: dict[str, Any],
    artifact_key: str,
    expected_format: str,
) -> None:
    artifact = artifacts.get(artifact_key)
    if not isinstance(artifact, dict):
        raise ValueError(f"manifest missing artifact: {artifact_key}")
    if artifact.get("format") != expected_format:
        raise ValueError(f"manifest artifact {artifact_key} format mismatch")
    artifact_path = artifact_root / str(artifact.get("path") or "")
    if not artifact_path.exists():
        raise ValueError(
            f"manifest artifact {artifact_key} does not exist: {artifact_path}"
        )
    if not artifact_path.is_file():
        raise ValueError(
            f"manifest artifact {artifact_key} must be a file: {artifact_path}"
        )
    if not artifact_path.read_text(encoding="utf-8").strip():
        raise ValueError(f"manifest artifact {artifact_key} must not be empty")


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"{path} does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _require_output_in_artifact_root(output_path: Path, artifact_root: Path) -> None:
    if output_path.parent.resolve() != artifact_root.resolve():
        raise ValueError("workspace snapshot output must stay in artifact directory")


def _require_bundle_identity(
    manifest: dict[str, Any],
    raw: dict[str, Any],
    scoring: dict[str, Any],
    review_queue: dict[str, Any],
    source_table: dict[str, Any],
    signal_trace: dict[str, Any],
) -> None:
    if raw.get("metadata", {}).get("fund_code") != manifest["fund_code"]:
        raise ValueError("workspace snapshot raw fund_code mismatch")
    if scoring.get("metadata", {}).get("fund_code") != manifest["fund_code"]:
        raise ValueError("workspace snapshot scoring fund_code mismatch")
    if source_table.get("fund_code") != manifest["fund_code"]:
        raise ValueError("workspace snapshot source table fund_code mismatch")
    if source_table.get("as_of_date") != manifest["as_of_date"]:
        raise ValueError("workspace snapshot source table as_of_date mismatch")
    if signal_trace.get("fund_code") != manifest["fund_code"]:
        raise ValueError("workspace snapshot signal trace fund_code mismatch")
    if signal_trace.get("as_of_date") != manifest["as_of_date"]:
        raise ValueError("workspace snapshot signal trace as_of_date mismatch")
    if review_queue.get("metadata", {}).get("fund_code") != manifest["fund_code"]:
        raise ValueError("workspace snapshot review queue fund_code mismatch")
    if review_queue.get("metadata", {}).get("as_of_date") != manifest["as_of_date"]:
        raise ValueError("workspace snapshot review queue as_of_date mismatch")
    if review_queue.get("metadata", {}).get("data_quality") != manifest["data_quality"]:
        raise ValueError("workspace snapshot review queue data_quality mismatch")
    if review_queue.get("fund", {}).get("fund_code") != manifest["fund_code"]:
        raise ValueError("workspace snapshot review queue fund_code mismatch")
    if review_queue.get("provider_foundation") != manifest["provider_foundation"]:
        raise ValueError("workspace snapshot review queue provider_foundation mismatch")
    if source_table.get("provider_foundation") != manifest["provider_foundation"]:
        raise ValueError("workspace snapshot source table provider_foundation mismatch")
    if scoring.get("provider_foundation") != manifest["provider_foundation"]:
        raise ValueError("workspace snapshot scoring provider_foundation mismatch")
    if raw.get("provider_foundation") != manifest["provider_foundation"]:
        raise ValueError("workspace snapshot raw provider_foundation mismatch")
    _validate_optional_bundle_payloads(raw, scoring)


def _validate_optional_bundle_payloads(raw: dict[str, Any], scoring: dict[str, Any]) -> None:
    raw_valuation = raw.get("valuation_snapshots")
    scoring_valuation = scoring.get("valuation_snapshots")
    if raw_valuation is not None or scoring_valuation is not None:
        if raw_valuation != scoring_valuation:
            raise ValueError("workspace snapshot valuation_snapshots mismatch")
        validate_valuation_snapshot_payload(raw_valuation)

    raw_news = raw.get("news_evidence")
    scoring_news = scoring.get("news_evidence")
    if raw_news is not None or scoring_news is not None:
        if raw_news != scoring_news:
            raise ValueError("workspace snapshot news_evidence mismatch")
        validate_news_evidence_payload(raw_news)

    raw_financial_metrics = raw.get("financial_metrics")
    scoring_financial_metrics = scoring.get("financial_metrics")
    if raw_financial_metrics is not None or scoring_financial_metrics is not None:
        if raw_financial_metrics != scoring_financial_metrics:
            raise ValueError("workspace snapshot financial_metrics mismatch")
        validate_financial_metrics_payload(raw_financial_metrics)
