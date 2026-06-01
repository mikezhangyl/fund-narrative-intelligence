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
from src.product_shell.workspace_store import (  # noqa: E402
    JsonWorkspaceRepository,
    build_workspace_export_package,
    import_workspace_export_package,
    render_workspace_state_html,
    write_workspace_export_package,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage local product-shell workspace state and saved views."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    save_view = subparsers.add_parser("save-view", help="Create or update a saved product-shell view.")
    save_view.add_argument("--store", type=Path, default=DEFAULT_OUTPUT_DIR / "product_shell" / "workspace_state.json")
    save_view.add_argument("--html", type=Path, default=None)
    save_view.add_argument("--view-id", required=True)
    save_view.add_argument("--label", required=True)
    save_view.add_argument("--surface", required=True)
    save_view.add_argument("--selected-route", default="")
    save_view.add_argument("--filters-json", default="{}")
    save_view.add_argument("--sorting-json", default="{}")
    save_view.add_argument("--updated-at", default=None)
    set_preferences = subparsers.add_parser("set-preferences", help="Update local workflow defaults.")
    set_preferences.add_argument("--store", type=Path, default=DEFAULT_OUTPUT_DIR / "product_shell" / "workspace_state.json")
    set_preferences.add_argument("--html", type=Path, default=None)
    set_preferences.add_argument("--default-surface", default=None)
    set_preferences.add_argument("--default-watchlist", default="")
    set_preferences.add_argument("--date-window-preset", default=None)
    set_preferences.add_argument("--display-density", default=None)
    set_preferences.add_argument("--theme", default=None)
    set_preferences.add_argument("--default-mode", default=None)
    set_preferences.add_argument("--preferences-json", default="{}")
    set_preferences.add_argument("--updated-at", default=None)
    export_parser = subparsers.add_parser("export", help="Export local workspace state.")
    export_parser.add_argument("--store", type=Path, default=DEFAULT_OUTPUT_DIR / "product_shell" / "workspace_state.json")
    export_parser.add_argument("--artifact-index", type=Path, default=None)
    export_parser.add_argument("--package", type=Path, required=True)
    export_parser.add_argument("--html", type=Path, default=None)
    export_parser.add_argument("--generated-at", default=None)
    import_parser = subparsers.add_parser("import", help="Import local workspace state.")
    import_parser.add_argument("--store", type=Path, default=DEFAULT_OUTPUT_DIR / "product_shell" / "workspace_state.json")
    import_parser.add_argument("--package", type=Path, required=True)
    import_parser.add_argument("--html", type=Path, default=None)
    import_parser.add_argument("--imported-at", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "save-view":
        return _save_view(args)
    if args.command == "set-preferences":
        return _set_preferences(args)
    if args.command == "export":
        return _export_workspace(args)
    if args.command == "import":
        return _import_workspace(args)
    return 2


def _save_view(args: argparse.Namespace) -> int:
    repository = JsonWorkspaceRepository(args.store)
    state = repository.upsert_saved_view(
        {
            "view_id": args.view_id,
            "label": args.label,
            "surface": args.surface,
            "selected_route": args.selected_route,
            "filters": _json_object(args.filters_json, "--filters-json"),
            "sorting": _json_object(args.sorting_json, "--sorting-json"),
        },
        updated_at=args.updated_at,
    )
    html_path = args.html or args.store.with_suffix(".html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_workspace_state_html(state), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "saved",
                "store": str(args.store),
                "html": str(html_path),
                "saved_view_count": state["summary"]["saved_view_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _export_workspace(args: argparse.Namespace) -> int:
    repository = JsonWorkspaceRepository(args.store)
    artifact_index = _read_json(args.artifact_index) if args.artifact_index is not None else None
    package = build_workspace_export_package(
        workspace_state=repository.load(),
        artifact_index=artifact_index,
        generated_at=args.generated_at,
    )
    write_workspace_export_package(
        package_path=args.package,
        package=package,
        html_path=args.html,
    )
    print(
        json.dumps(
            {
                "status": "exported",
                "package": str(args.package),
                "html": str(args.html) if args.html is not None else "",
                "export_id": package["manifest"]["export_id"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _import_workspace(args: argparse.Namespace) -> int:
    package = _read_json(args.package)
    state = import_workspace_export_package(
        package,
        JsonWorkspaceRepository(args.store),
        imported_at=args.imported_at,
    )
    if args.html is not None:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_workspace_state_html(state), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "imported",
                "store": str(args.store),
                "html": str(args.html) if args.html is not None else "",
                "source_export_id": state["import_metadata"]["source_export_id"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _set_preferences(args: argparse.Namespace) -> int:
    preferences = _json_object(args.preferences_json, "--preferences-json")
    if args.default_surface is not None:
        preferences["default_surface"] = args.default_surface
    if args.default_watchlist:
        preferences["default_watchlist"] = [
            item.strip()
            for item in args.default_watchlist.split(",")
            if item.strip()
        ]
    if args.date_window_preset is not None:
        preferences["preferred_date_window"] = {"preset": args.date_window_preset}
    if args.display_density is not None:
        preferences["display_density"] = args.display_density
    if args.theme is not None:
        preferences["theme"] = args.theme
    if args.default_mode is not None:
        preferences["default_mode"] = args.default_mode
    repository = JsonWorkspaceRepository(args.store)
    state = repository.set_preferences(preferences, updated_at=args.updated_at)
    html_path = args.html or args.store.with_suffix(".html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_workspace_state_html(state), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "saved",
                "store": str(args.store),
                "html": str(html_path),
                "default_surface": state["preferences"]["default_surface"],
                "preference_redaction_count": state["summary"]["preference_redaction_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def _json_object(value: str, option_name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{option_name} must be a JSON object: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SystemExit(f"{option_name} must be a JSON object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
