from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

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
    build_release_preflight,
    render_config_preflight_html,
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
from src.product_shell.workspace_store import (  # noqa: E402
    JsonWorkspaceRepository,
    render_workspace_state_html,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the local FNI product shell static artifacts."
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "product_shell",
    )
    parser.add_argument(
        "--workspace-store",
        type=Path,
        default=None,
        help="Path to the local product-shell workspace state JSON store.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    route_registry = build_product_shell_route_registry(
        artifact_index_path=str(output_dir / "artifact_index.json")
    )
    project_root = _project_root_for_artifact_root(args.artifact_root)
    artifact_index = build_artifact_index(
        output_root=args.artifact_root,
        project_root=project_root,
    )
    narrative_data = build_narrative_data_snapshot(
        project_root=project_root,
        output_root=args.artifact_root,
    )
    preflight = build_release_preflight(
        project_root=project_root,
        output_root=args.artifact_root,
        mode="demo",
    )
    source_quality = build_source_quality_dashboard(
        project_root=project_root,
        output_root=args.artifact_root,
    )
    workspace_store_path = args.workspace_store or (output_dir / "workspace_state.json")
    workspace_repository = JsonWorkspaceRepository(workspace_store_path)
    workspace_state = workspace_repository.load()
    if not workspace_store_path.exists():
        workspace_repository.save(workspace_state)
    shell = build_product_shell_payload(
        route_registry=route_registry,
        artifact_index=artifact_index,
        narrative_data=narrative_data,
        workspace_state=workspace_state,
    )
    _write_json(output_dir / "route_registry.json", route_registry)
    _write_text(output_dir / "route_registry.html", render_route_registry_preview(route_registry))
    _write_json(output_dir / "artifact_index.json", artifact_index)
    _write_text(output_dir / "artifact_index.html", render_artifact_index_html(artifact_index))
    _write_json(output_dir / "narrative_data.json", narrative_data)
    _write_text(output_dir / "narrative_data.html", render_narrative_data_html(narrative_data))
    _write_json(output_dir / "product_shell.json", shell)
    _write_text(output_dir / "index.html", render_product_home_html(shell))
    _write_text(output_dir / "artifact_browser.html", render_artifact_browser_html(shell))
    _write_json(output_dir / "workspace_state.json", workspace_state)
    _write_text(output_dir / "workspace_state.html", render_workspace_state_html(workspace_state))
    _write_json(output_dir / "config_preflight.json", preflight)
    _write_text(output_dir / "config_preflight.html", render_config_preflight_html(preflight))
    _write_json(output_dir / "source_quality_dashboard.json", source_quality)
    _write_text(
        output_dir / "source_quality_dashboard.html",
        render_source_quality_dashboard_html(source_quality),
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "route_registry_json": str(output_dir / "route_registry.json"),
                "route_registry_html": str(output_dir / "route_registry.html"),
                "artifact_index_json": str(output_dir / "artifact_index.json"),
                "artifact_index_html": str(output_dir / "artifact_index.html"),
                "narrative_data_json": str(output_dir / "narrative_data.json"),
                "narrative_data_html": str(output_dir / "narrative_data.html"),
                "home_html": str(output_dir / "index.html"),
                "artifact_browser_html": str(output_dir / "artifact_browser.html"),
                "workspace_state_json": str(output_dir / "workspace_state.json"),
                "workspace_state_html": str(output_dir / "workspace_state.html"),
                "config_preflight_json": str(output_dir / "config_preflight.json"),
                "config_preflight_html": str(output_dir / "config_preflight.html"),
                "source_quality_dashboard_json": str(output_dir / "source_quality_dashboard.json"),
                "source_quality_dashboard_html": str(output_dir / "source_quality_dashboard.html"),
            },
            ensure_ascii=False,
        )
    )
    return 0


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
