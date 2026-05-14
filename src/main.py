from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.announcement_smoke import run_announcement_evidence_smoke
from src.config import DEFAULT_OUTPUT_DIR, FIXTURE_DIR
from src.errors import PipelineError
from src.modules.narrative_review.persistence import persist_review_action_registry
from src.modules.narrative_review.preview import write_review_action_preview
from src.orchestrator import (
    STOCK_MAPPING_MODE_FIXTURE,
    STOCK_MAPPING_MODES,
    inspect_provider_foundation,
    run_all_fixture_pipelines,
    run_pipeline,
)
from src.providers.mock import MockDataProvider
from src.real_fund_smoke import run_real_fund_smoke
from src.validation import (
    validate_pipeline_artifact_manifest_payload,
    validate_review_action_persistence_result_payload,
    validate_review_action_preview_payload,
    validate_review_queue_artifact_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a V1 fund narrative intelligence report."
    )
    parser.add_argument("--fund-code", help="Fund code to analyze.")
    parser.add_argument(
        "--provider-mode",
        choices=["mock", "real", "eastmoney"],
        default="mock",
        help="Provider mode. V1 real mode falls back to mock fixtures; eastmoney tries no-key fund holdings.",
    )
    parser.add_argument(
        "--stock-mapping-mode",
        choices=sorted(STOCK_MAPPING_MODES),
        default=STOCK_MAPPING_MODE_FIXTURE,
        help=(
            "Stock-to-narrative mapping mode. Default uses explicit fixture "
            "mappings plus registry-rule fallback; registry-rule derives "
            "mappings from current holdings and Narrative Registry terms only."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated artifacts.",
    )
    parser.add_argument(
        "--list-fixtures",
        action="store_true",
        help="List available mock fund-code fixtures and exit.",
    )
    parser.add_argument(
        "--run-all-fixtures",
        action="store_true",
        help="Run the pipeline for every available mock fund fixture.",
    )
    parser.add_argument(
        "--run-real-smoke",
        action="store_true",
        help="Run the Eastmoney real-fund smoke set and write summary artifacts.",
    )
    parser.add_argument(
        "--run-announcement-smoke",
        action="store_true",
        help="Run the Eastmoney + CNINFO announcement evidence smoke set and write summary artifacts.",
    )
    parser.add_argument(
        "--provider-diagnostics",
        action="store_true",
        help="Print provider foundation diagnostics as JSON without generating report artifacts.",
    )
    parser.add_argument(
        "--preview-review-action",
        help=(
            "Preview one candidate narrative review action JSON without mutating the "
            "source registry."
        ),
    )
    parser.add_argument(
        "--persist-review-action",
        help=(
            "Persist one candidate narrative review action JSON to an explicit "
            "registry output path."
        ),
    )
    parser.add_argument(
        "--registry-path",
        default=str(FIXTURE_DIR / "narrative_registry.json"),
        help="Narrative registry JSON used by --preview-review-action.",
    )
    parser.add_argument(
        "--review-action-output",
        help="Optional explicit output path for --preview-review-action.",
    )
    parser.add_argument(
        "--registry-output",
        help="Required output registry JSON path for --persist-review-action.",
    )
    parser.add_argument(
        "--allow-registry-overwrite",
        action="store_true",
        help="Allow --persist-review-action to overwrite --registry-path in place.",
    )
    parser.add_argument(
        "--allow-registry-output-overwrite",
        action="store_true",
        help="Allow --persist-review-action to overwrite an existing non-source registry output file.",
    )
    parser.add_argument(
        "--persistence-result-output",
        help="Optional explicit persistence result artifact path for --persist-review-action.",
    )
    parser.add_argument(
        "--allow-persistence-result-overwrite",
        action="store_true",
        help="Allow --persist-review-action to overwrite an existing persistence result artifact.",
    )
    parser.add_argument(
        "--validate-persistence-result",
        help="Validate a review-action persistence result artifact and exit.",
    )
    parser.add_argument(
        "--validate-review-preview",
        help="Validate a review-action preview artifact and exit.",
    )
    parser.add_argument(
        "--validate-review-queue",
        help="Validate a fund review-queue artifact and exit.",
    )
    parser.add_argument(
        "--validate-artifact-manifest",
        help="Validate a pipeline artifact manifest and exit.",
    )
    parser.add_argument(
        "--validate-artifact-contracts",
        help=(
            "Validate all known artifact contracts from a manifest file or output "
            "directory and exit."
        ),
    )
    parser.add_argument(
        "--include-cninfo-announcements",
        action="store_true",
        help="Optionally fetch CNINFO announcement metadata and convert it into evidence records.",
    )
    parser.add_argument(
        "--include-market-quotes",
        "--include-eastmoney-quotes",
        dest="include_market_quotes",
        action="store_true",
        help="Optionally fetch real market quote snapshots for current holdings.",
    )
    parser.add_argument(
        "--announcement-start-date",
        help="Optional ISO start date for CNINFO announcement search when --include-cninfo-announcements is set.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.announcement_start_date and not args.include_cninfo_announcements:
        parser.error(
            "--announcement-start-date requires --include-cninfo-announcements"
        )
    if args.review_action_output and not args.preview_review_action:
        parser.error("--review-action-output requires --preview-review-action")
    if args.registry_output and not args.persist_review_action:
        parser.error("--registry-output requires --persist-review-action")
    if args.allow_registry_overwrite and not args.persist_review_action:
        parser.error("--allow-registry-overwrite requires --persist-review-action")
    if args.allow_registry_output_overwrite and not args.persist_review_action:
        parser.error("--allow-registry-output-overwrite requires --persist-review-action")
    if args.persistence_result_output and not args.persist_review_action:
        parser.error("--persistence-result-output requires --persist-review-action")
    if args.allow_persistence_result_overwrite and not args.persist_review_action:
        parser.error("--allow-persistence-result-overwrite requires --persist-review-action")
    if args.preview_review_action and args.persist_review_action:
        parser.error("--preview-review-action and --persist-review-action are mutually exclusive")
    if args.validate_persistence_result and (
        args.preview_review_action or args.persist_review_action
    ):
        parser.error(
            "--validate-persistence-result cannot be combined with review action execution"
        )
    if args.validate_review_preview and (
        args.preview_review_action or args.persist_review_action
    ):
        parser.error(
            "--validate-review-preview cannot be combined with review action execution"
        )
    if args.validate_review_queue and (
        args.preview_review_action or args.persist_review_action
    ):
        parser.error(
            "--validate-review-queue cannot be combined with review action execution"
        )
    if args.validate_artifact_manifest and (
        args.preview_review_action or args.persist_review_action
    ):
        parser.error(
            "--validate-artifact-manifest cannot be combined with review action execution"
        )
    if args.validate_artifact_contracts and (
        args.preview_review_action or args.persist_review_action
    ):
        parser.error(
            "--validate-artifact-contracts cannot be combined with review action execution"
        )
    if (
        args.stock_mapping_mode != STOCK_MAPPING_MODE_FIXTURE
        and _uses_non_pipeline_action(args)
    ):
        parser.error(
            "--stock-mapping-mode is only supported with single --fund-code report generation"
        )

    if args.validate_review_preview:
        try:
            payload = _read_json_object(Path(args.validate_review_preview))
            validate_review_action_preview_payload(payload)
        except PipelineError as exc:
            parser.error(str(exc))
            return 2
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(
                f"Unrecoverable review preview validation error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("Review preview valid:")
        print(Path(args.validate_review_preview))
        return 0

    if args.validate_review_queue:
        try:
            payload = _read_json_object(Path(args.validate_review_queue))
            validate_review_queue_artifact_payload(payload)
        except PipelineError as exc:
            parser.error(str(exc))
            return 2
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(
                f"Unrecoverable review queue validation error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("Review queue valid:")
        print(Path(args.validate_review_queue))
        return 0

    if args.validate_artifact_manifest:
        try:
            payload = _read_json_object(Path(args.validate_artifact_manifest))
            validate_pipeline_artifact_manifest_payload(payload)
        except PipelineError as exc:
            parser.error(str(exc))
            return 2
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(
                f"Unrecoverable artifact manifest validation error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("Artifact manifest valid:")
        print(Path(args.validate_artifact_manifest))
        return 0

    if args.validate_artifact_contracts:
        try:
            summary = _validate_artifact_contracts(
                Path(args.validate_artifact_contracts)
            )
        except PipelineError as exc:
            parser.error(str(exc))
            return 2
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(
                f"Unrecoverable artifact contract validation error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("Artifact contracts valid:")
        print(Path(args.validate_artifact_contracts))
        print(
            " ".join(
                [
                    f"manifests={summary['manifests']}",
                    f"review_queues={summary['review_queues']}",
                    f"review_previews={summary['review_previews']}",
                    f"persistence_results={summary['persistence_results']}",
                ]
            )
        )
        return 0

    if args.validate_persistence_result:
        try:
            payload = _read_json_object(Path(args.validate_persistence_result))
            validate_review_action_persistence_result_payload(payload)
        except PipelineError as exc:
            parser.error(str(exc))
            return 2
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(
                f"Unrecoverable persistence result validation error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("Persistence result valid:")
        print(Path(args.validate_persistence_result))
        return 0

    if args.preview_review_action:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements is not supported with --preview-review-action")
        if args.include_market_quotes:
            parser.error("--include-market-quotes is not supported with --preview-review-action")
        try:
            output_path = write_review_action_preview(
                registry_path=Path(args.registry_path),
                action_path=Path(args.preview_review_action),
                output_dir=Path(args.output_dir),
                output_path=Path(args.review_action_output)
                if args.review_action_output
                else None,
            )
        except PipelineError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(f"Unrecoverable review action preview error: {exc}", file=sys.stderr)
            return 1

        print("Review action preview:")
        print(output_path)
        return 0

    if args.persist_review_action:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements is not supported with --persist-review-action")
        if args.include_market_quotes:
            parser.error("--include-market-quotes is not supported with --persist-review-action")
        if not args.registry_output:
            parser.error("--registry-output is required with --persist-review-action")
        try:
            result = persist_review_action_registry(
                registry_path=Path(args.registry_path),
                action_path=Path(args.persist_review_action),
                registry_output_path=Path(args.registry_output),
                result_output_path=Path(args.persistence_result_output)
                if args.persistence_result_output
                else None,
                result_output_dir=Path(args.output_dir),
                allow_registry_overwrite=args.allow_registry_overwrite,
                allow_output_overwrite=args.allow_registry_output_overwrite,
                allow_result_overwrite=args.allow_persistence_result_overwrite,
            )
        except PipelineError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(
                f"Unrecoverable review action persistence error: {exc}",
                file=sys.stderr,
            )
            return 1

        print("Review action persisted:")
        print(result["registry_output_path"])
        if "persistence_result_path" in result:
            print(result["persistence_result_path"])
        return 0

    if args.list_fixtures:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements requires --fund-code")
        if args.include_market_quotes:
            parser.error("--include-market-quotes requires --fund-code")
        for fund_code in MockDataProvider().list_fund_codes():
            print(fund_code)
        return 0

    if args.run_all_fixtures:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements is not supported with --run-all-fixtures")
        if args.include_market_quotes:
            parser.error("--include-market-quotes is not supported with --run-all-fixtures")
        try:
            results = run_all_fixture_pipelines(
                provider_mode=args.provider_mode,
                output_dir=args.output_dir,
            )
        except PipelineError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Unrecoverable pipeline error: {exc}", file=sys.stderr)
            return 1

        print("Generated fixture artifacts:")
        for fund_code, artifacts in results.items():
            print(fund_code)
            for path in artifacts.values():
                print(path)
        return 0

    if args.run_real_smoke:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements is not supported with --run-real-smoke")
        if args.include_market_quotes:
            parser.error("--include-market-quotes is not supported with --run-real-smoke")
        try:
            summary = run_real_fund_smoke(output_dir=args.output_dir)
        except PipelineError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Unrecoverable pipeline error: {exc}", file=sys.stderr)
            return 1

        print("Real fund smoke summary:")
        print(f"status={summary['status']}")
        for result in summary["funds"]:
            print(
                f"{result['fund_code']} {result['scenario']} "
                f"{result['primary_narrative']} {result['stage']} "
                f"coverage={result['coverage_ratio']:.0%} "
                f"precision_flags={result.get('mapping_precision_flag_count', 0)} "
                f"excluded_candidates={result.get('excluded_mapping_candidate_count', 0)} "
                f"candidate_narratives={result.get('candidate_narrative_count', 0)} "
                f"review_queue={result.get('candidate_review_queue_item_count', 0)}"
            )
        return 0 if summary["status"] == "passed" else 1

    if args.run_announcement_smoke:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements is not supported with --run-announcement-smoke")
        if args.include_market_quotes:
            parser.error("--include-market-quotes is not supported with --run-announcement-smoke")
        try:
            summary = run_announcement_evidence_smoke(output_dir=args.output_dir)
        except PipelineError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Unrecoverable announcement smoke error: {exc}", file=sys.stderr)
            return 1

        print("Announcement evidence smoke summary:")
        print(f"status={summary['status']}")
        for result in summary["cases"]:
            print(
                f"{result['fund_code']} {result['scenario']} "
                f"announcements={result['announcement_count']} "
                f"evidence={result['announcement_evidence_count']} "
                f"notice={'yes' if result['data_source_notice_required'] else 'no'} "
                f"quality={result['effective_data_quality']}"
            )
        return 0 if summary["status"] == "passed" else 1

    if args.provider_diagnostics:
        if args.include_cninfo_announcements:
            parser.error("--include-cninfo-announcements is not supported with --provider-diagnostics")
        if args.include_market_quotes:
            parser.error("--include-market-quotes is not supported with --provider-diagnostics")
        if not args.fund_code:
            parser.error("--fund-code is required with --provider-diagnostics")
            return 2
        try:
            diagnostics = inspect_provider_foundation(
                fund_code=args.fund_code,
                provider_mode=args.provider_mode,
            )
        except PipelineError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        except Exception as exc:
            print(f"Unrecoverable provider diagnostics error: {exc}", file=sys.stderr)
            return 1

        print(json.dumps(diagnostics, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if not args.fund_code:
        parser.error(
            "--fund-code is required unless --list-fixtures, --run-all-fixtures, --run-real-smoke, --run-announcement-smoke, or --provider-diagnostics is used"
        )
        return 2

    try:
        artifacts = run_pipeline(
            fund_code=args.fund_code,
            provider_mode=args.provider_mode,
            output_dir=args.output_dir,
            include_announcement_evidence=args.include_cninfo_announcements,
            announcement_start_date=args.announcement_start_date,
            include_market_quotes=args.include_market_quotes,
            stock_mapping_mode=args.stock_mapping_mode,
        )
    except PipelineError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    except Exception as exc:
        print(f"Unrecoverable pipeline error: {exc}", file=sys.stderr)
        return 1

    print("Generated artifacts:")
    for path in artifacts.values():
        print(path)
    return 0


def _read_json_object(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"{path} does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _uses_non_pipeline_action(args: argparse.Namespace) -> bool:
    return any(
        bool(value)
        for value in (
            args.list_fixtures,
            args.run_all_fixtures,
            args.run_real_smoke,
            args.run_announcement_smoke,
            args.provider_diagnostics,
            args.preview_review_action,
            args.persist_review_action,
            args.validate_persistence_result,
            args.validate_review_preview,
            args.validate_review_queue,
            args.validate_artifact_manifest,
            args.validate_artifact_contracts,
        )
    )


def _validate_artifact_contracts(path: Path) -> dict[str, int]:
    if path.is_dir():
        return _validate_artifact_contract_directory(path)
    if path.is_file():
        summary = _empty_contract_summary()
        _validate_manifest_bundle(path)
        summary["manifests"] = 1
        return summary
    raise ValueError(f"{path} does not exist")


def _validate_artifact_contract_directory(path: Path) -> dict[str, int]:
    summary = _empty_contract_summary()

    for manifest_path in sorted(path.glob("fund_*_manifest.json")):
        _validate_manifest_bundle(manifest_path)
        summary["manifests"] += 1
    for queue_path in sorted(path.glob("fund_*_review_queue.json")):
        validate_review_queue_artifact_payload(_read_json_object(queue_path))
        summary["review_queues"] += 1
    for preview_path in sorted(path.glob("candidate_review_action_*_preview.json")):
        validate_review_action_preview_payload(_read_json_object(preview_path))
        summary["review_previews"] += 1
    for result_path in sorted(path.glob("candidate_review_action_*_persistence.json")):
        validate_review_action_persistence_result_payload(
            _read_json_object(result_path)
        )
        summary["persistence_results"] += 1

    if not any(summary.values()):
        raise ValueError(f"{path} contains no known artifact contracts")
    return summary


def _validate_manifest_bundle(manifest_path: Path) -> None:
    manifest = _read_json_object(manifest_path)
    validate_pipeline_artifact_manifest_payload(manifest)
    artifact_root = manifest_path.parent
    for artifact_key, artifact in manifest["artifacts"].items():
        artifact_path = artifact_root / artifact["path"]
        if not artifact_path.exists():
            raise ValueError(
                f"manifest artifact {artifact_key} does not exist: {artifact_path}"
            )
        if not artifact_path.is_file():
            raise ValueError(
                f"manifest artifact {artifact_key} must be a file: {artifact_path}"
            )
        _validate_manifest_referenced_artifact(
            artifact_key=artifact_key,
            artifact_path=artifact_path,
            manifest=manifest,
        )


def _validate_manifest_referenced_artifact(
    artifact_key: str,
    artifact_path: Path,
    manifest: dict,
) -> None:
    if artifact_key == "review_queue":
        validate_review_queue_artifact_payload(_read_json_object(artifact_path))
        return
    if artifact_key in {"raw", "scoring"}:
        payload = _read_json_object(artifact_path)
        _validate_manifest_json_metadata(
            payload=payload,
            manifest=manifest,
            artifact_key=artifact_key,
        )
        return
    text = artifact_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"manifest artifact {artifact_key} must not be empty")


def _validate_manifest_json_metadata(
    payload: dict,
    manifest: dict,
    artifact_key: str,
) -> None:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError(f"manifest artifact {artifact_key} missing metadata object")
    if metadata.get("fund_code") != manifest["fund_code"]:
        raise ValueError(f"manifest artifact {artifact_key} fund_code mismatch")
    if payload.get("provider_foundation") != manifest["provider_foundation"]:
        raise ValueError(
            f"manifest artifact {artifact_key} provider_foundation mismatch"
        )


def _empty_contract_summary() -> dict[str, int]:
    return {
        "manifests": 0,
        "review_queues": 0,
        "review_previews": 0,
        "persistence_results": 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
