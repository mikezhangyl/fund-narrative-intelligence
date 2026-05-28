from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation import validate_review_queue_artifact_payload  # noqa: E402


class AcceptanceError(ValueError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate narrative-intelligence-service artifacts."
    )
    parser.add_argument("--fund-code", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--require-generated-candidates", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_acceptance_outputs(
            output_dir=args.output_dir,
            fund_code=args.fund_code,
            require_generated_candidates=args.require_generated_candidates,
        )
    except AcceptanceError as exc:
        print(f"Narrative intelligence validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        "narrative_intelligence_service=passed "
        f"fund_code={args.fund_code} generated_candidates="
        f"{'required' if args.require_generated_candidates else 'optional'}"
    )
    return 0


def validate_acceptance_outputs(
    *,
    output_dir: Path,
    fund_code: str,
    require_generated_candidates: bool = False,
) -> None:
    raw = _read_json(output_dir / f"fund_{fund_code}_raw.json")
    scoring = _read_json(output_dir / f"fund_{fund_code}_scoring.json")
    review_queue = _read_json(output_dir / f"fund_{fund_code}_review_queue.json")
    validate_review_queue_artifact_payload(review_queue)

    for payload_name, payload in {"raw": raw, "scoring": scoring}.items():
        _require_mapping(payload.get("source_item_stats"), f"{payload_name}.source_item_stats")
        _require_mapping(payload.get("candidate_seeds"), f"{payload_name}.candidate_seeds")
        _require_mapping(payload.get("mapping_proposals"), f"{payload_name}.mapping_proposals")
        _require_mapping(
            payload.get("narrative_evidence"),
            f"{payload_name}.narrative_evidence",
        )
        _require_mapping(payload.get("diagnostics"), f"{payload_name}.diagnostics")
        if not isinstance(payload.get("source_items"), list):
            raise AcceptanceError(f"{payload_name}.source_items must be a list")
        if not isinstance(payload.get("candidate_narratives"), list):
            raise AcceptanceError(f"{payload_name}.candidate_narratives must be a list")
        if not isinstance(payload.get("generated_candidate_narratives"), list):
            raise AcceptanceError(
                f"{payload_name}.generated_candidate_narratives must be a list"
            )

    if raw["diagnostics"] != scoring["diagnostics"]:
        raise AcceptanceError("raw and scoring diagnostics must match")
    if raw["candidate_narratives"] != scoring["candidate_narratives"]:
        raise AcceptanceError("raw and scoring candidate_narratives must match")
    if raw["mapping_proposals"] != scoring["mapping_proposals"]:
        raise AcceptanceError("raw and scoring mapping_proposals must match")
    if raw["narrative_evidence"] != scoring["narrative_evidence"]:
        raise AcceptanceError("raw and scoring narrative_evidence must match")
    if review_queue["candidate_narratives"] != scoring["candidate_narratives"]:
        raise AcceptanceError("review queue candidate_narratives must match scoring")

    if require_generated_candidates:
        generated = raw["generated_candidate_narratives"]
        if not generated:
            raise AcceptanceError("generated candidate narratives are required")
        if raw.get("narrative_generation_enabled") is not True:
            raise AcceptanceError("narrative_generation_enabled must be true")
        proposal_count = raw["mapping_proposals"]["summary"]["proposal_count"]
        if proposal_count < len(generated):
            raise AcceptanceError(
                "mapping proposals must cover every generated candidate narrative"
            )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AcceptanceError(f"missing artifact: {path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AcceptanceError(f"{path.name} must contain a JSON object")
    return payload


def _require_mapping(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise AcceptanceError(f"{context} must be an object")


if __name__ == "__main__":
    raise SystemExit(main())
