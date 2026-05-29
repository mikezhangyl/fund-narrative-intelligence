from __future__ import annotations

import argparse
from pathlib import Path

from stock_narrative_service.app import create_server
from stock_narrative_service.config import ServiceConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Stock Narrative Service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--registry-path", type=Path)
    parser.add_argument("--mappings-path", type=Path)
    parser.add_argument("--evidence-packs-path", type=Path)
    parser.add_argument("--candidate-events-path", type=Path)
    parser.add_argument("--intake-ledger-path", type=Path)
    parser.add_argument("--review-actions-path", type=Path)
    parser.add_argument("--promotion-decisions-path", type=Path)
    parser.add_argument("--job-definitions-path", type=Path)
    parser.add_argument("--job-runs-path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = _config_from_args(args)
    server = create_server((args.host, args.port), config=config)
    print(f"stock-narrative-service listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _config_from_args(args: argparse.Namespace) -> ServiceConfig:
    defaults = ServiceConfig()
    return ServiceConfig(
        registry_path=args.registry_path or defaults.registry_path,
        mappings_path=args.mappings_path or defaults.mappings_path,
        evidence_packs_path=args.evidence_packs_path or defaults.evidence_packs_path,
        candidate_events_path=args.candidate_events_path or defaults.candidate_events_path,
        intake_ledger_path=args.intake_ledger_path or defaults.intake_ledger_path,
        review_actions_path=args.review_actions_path or defaults.review_actions_path,
        promotion_decisions_path=(
            args.promotion_decisions_path or defaults.promotion_decisions_path
        ),
        job_definitions_path=args.job_definitions_path or defaults.job_definitions_path,
        job_runs_path=args.job_runs_path or defaults.job_runs_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
