from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.product_shell.artifact_index import (  # noqa: E402
    build_artifact_index,
    render_artifact_index_html,
)
from src.product_shell.narrative_data import (  # noqa: E402
    build_narrative_data_snapshot,
    render_narrative_data_html,
)
from src.product_shell.release import (  # noqa: E402
    build_acceptance_checklist,
    build_release_manifest,
    build_release_preflight,
    render_acceptance_checklist_html,
    render_config_preflight_html,
    render_release_manifest_html,
)
from src.product_shell.route_registry import (  # noqa: E402
    build_product_shell_route_registry,
    render_route_registry_preview,
)
from src.product_shell.shell import (  # noqa: E402
    build_product_shell_payload,
    render_artifact_browser_html,
    render_product_home_html,
)
from src.product_shell.source_quality import (  # noqa: E402
    build_source_quality_dashboard,
    render_source_quality_dashboard_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and verify the local FNI product shell release package."
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "product_shell" / "round8-current",
    )
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    return parser


def main(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    environment = dict(os.environ if env is None else env)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    project_root = _project_root_for_artifact_root(args.artifact_root)

    route_registry = build_product_shell_route_registry(
        artifact_index_path=str(output_dir / "artifact_index.json")
    )
    artifact_index = build_artifact_index(
        output_root=args.artifact_root,
        project_root=project_root,
    )
    narrative_data = build_narrative_data_snapshot(
        project_root=project_root,
        output_root=args.artifact_root,
    )
    shell = build_product_shell_payload(
        route_registry=route_registry,
        artifact_index=artifact_index,
        narrative_data=narrative_data,
    )
    preflight = build_release_preflight(
        project_root=project_root,
        output_root=args.artifact_root,
        mode=args.mode,
        env=environment,
    )
    source_quality = build_source_quality_dashboard(
        project_root=project_root,
        output_root=args.artifact_root,
    )

    _write_shell_outputs(
        output_dir,
        route_registry,
        artifact_index,
        narrative_data,
        shell,
        preflight,
        source_quality,
    )
    manifest = build_release_manifest(
        output_dir=output_dir,
        preflight=preflight,
        mode=args.mode,
    )
    checklist = build_acceptance_checklist(
        manifest=manifest,
        preflight=preflight,
    )
    _write_json(output_dir / "release_manifest.json", manifest)
    _write_text(output_dir / "release_manifest.html", render_release_manifest_html(manifest))
    _write_json(output_dir / "acceptance_checklist.json", checklist)
    _write_text(
        output_dir / "acceptance_checklist.html",
        render_acceptance_checklist_html(checklist),
    )
    print(
        json.dumps(
            {
                "status": checklist["status"],
                "mode": args.mode,
                "release_manifest": str(output_dir / "release_manifest.json"),
                "acceptance_checklist": str(output_dir / "acceptance_checklist.json"),
                "config_preflight": str(output_dir / "config_preflight.json"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if checklist["status"] == "pass" else 1


def _write_shell_outputs(
    output_dir: Path,
    route_registry: dict[str, Any],
    artifact_index: dict[str, Any],
    narrative_data: dict[str, Any],
    shell: dict[str, Any],
    preflight: dict[str, Any],
    source_quality: dict[str, Any],
) -> None:
    _write_json(output_dir / "route_registry.json", route_registry)
    _write_text(output_dir / "route_registry.html", render_route_registry_preview(route_registry))
    _write_json(output_dir / "artifact_index.json", artifact_index)
    _write_text(output_dir / "artifact_index.html", render_artifact_index_html(artifact_index))
    _write_json(output_dir / "narrative_data.json", narrative_data)
    _write_text(output_dir / "narrative_data.html", render_narrative_data_html(narrative_data))
    _write_json(output_dir / "product_shell.json", shell)
    _write_text(output_dir / "index.html", render_product_home_html(shell))
    _write_text(output_dir / "artifact_browser.html", render_artifact_browser_html(shell))
    _write_json(output_dir / "config_preflight.json", preflight)
    _write_text(output_dir / "config_preflight.html", render_config_preflight_html(preflight))
    _write_json(output_dir / "source_quality_dashboard.json", source_quality)
    _write_text(
        output_dir / "source_quality_dashboard.html",
        render_source_quality_dashboard_html(source_quality),
    )


def _project_root_for_artifact_root(artifact_root: Path) -> Path:
    resolved = artifact_root.resolve()
    if resolved.name == DEFAULT_OUTPUT_DIR.name:
        return resolved.parent
    return PROJECT_ROOT


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
