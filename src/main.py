from __future__ import annotations

import argparse
import sys

from src.config import DEFAULT_OUTPUT_DIR
from src.errors import PipelineError
from src.orchestrator import run_all_fixture_pipelines, run_pipeline
from src.providers.mock import MockDataProvider
from src.real_fund_smoke import run_real_fund_smoke


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_fixtures:
        for fund_code in MockDataProvider().list_fund_codes():
            print(fund_code)
        return 0

    if args.run_all_fixtures:
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
                f"coverage={result['coverage_ratio']:.0%}"
            )
        return 0 if summary["status"] == "passed" else 1

    if not args.fund_code:
        parser.error(
            "--fund-code is required unless --list-fixtures, --run-all-fixtures, or --run-real-smoke is used"
        )
        return 2

    try:
        artifacts = run_pipeline(
            fund_code=args.fund_code,
            provider_mode=args.provider_mode,
            output_dir=args.output_dir,
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


if __name__ == "__main__":
    raise SystemExit(main())
