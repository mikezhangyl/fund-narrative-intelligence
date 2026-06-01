from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any, Mapping

DEFAULT_GATEWAY_URL = "http://127.0.0.1:8700"
DEFAULT_NARRATIVE_SERVICE_URL = "http://127.0.0.1:8800"
SECRET_MARKERS = ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "CREDENTIAL")


def build_release_preflight(
    *,
    project_root: Path,
    output_root: Path,
    mode: str = "demo",
    env: Mapping[str, str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    normalized_mode = mode if mode in {"demo", "live"} else "demo"
    env_values = dict(env or {})
    checks = [
        _service_url_check(
            check_id="market_data_gateway_url",
            label="Market data gateway URL",
            env_name="MARKET_DATA_GATEWAY_URL",
            default_url=DEFAULT_GATEWAY_URL,
            required=normalized_mode == "live",
            env=env_values,
        ),
        _service_url_check(
            check_id="narrative_service_url",
            label="Narrative Service URL",
            env_name="NARRATIVE_SERVICE_URL",
            default_url=DEFAULT_NARRATIVE_SERVICE_URL,
            required=normalized_mode == "live",
            env=env_values,
        ),
        _path_check(
            check_id="output_root",
            label="Output root",
            path=output_root,
            project_root=project_root,
        ),
        _path_check(
            check_id="product_shell_output",
            label="Product shell output",
            path=output_root / "product_shell",
            project_root=project_root,
        ),
    ]
    secret_checks = _secret_checks(env_values)
    all_checks = checks + secret_checks
    degraded_count = sum(1 for check in all_checks if check.get("status") in {"missing", "degraded"})
    return {
        "version": "product-shell-release-preflight-v1",
        "generated_at": generated_at or _utc_now(),
        "mode": normalized_mode,
        "status": "degraded" if degraded_count else "ok",
        "summary": {
            "check_count": len(all_checks),
            "degraded_count": degraded_count,
            "missing_count": sum(1 for check in all_checks if check.get("status") == "missing"),
            "optional_missing_count": sum(
                1 for check in all_checks if check.get("status") == "optional_missing"
            ),
            "secret_redaction_count": len(secret_checks),
            "provider_smoke_executed": False,
        },
        "startup_order": _startup_order(),
        "checks": all_checks,
        "validation_command": _validation_command(normalized_mode),
        "safe_commands": [
            "uv run python scripts/build_product_shell.py --output-dir outputs/product_shell/round8-current",
            "uv run python scripts/run_product_shell_release_check.py --mode demo",
        ],
        "runbooks": [
            "docs/product/round8-interactive-product-shell-release-plan-2026-05-30.md",
            "docs/product/stock-narrative-service-runbook.md",
            "docs/product/market-data-gateway-boundary.md",
        ],
        "provider_smoke_policy": {
            "preflight_is_provider_smoke": False,
            "message": "预检不是 provider smoke；它只检查配置、路径和可运行命令，不访问外部 provider。",
        },
    }


def render_config_preflight_html(payload: dict[str, Any]) -> str:
    summary = _mapping(payload.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>配置与预检</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>配置与预检</h1>",
            '<section class="summary">',
            _html_kv("模式", payload.get("mode")),
            _html_kv("状态", payload.get("status")),
            _html_kv("检查项", summary.get("check_count", 0)),
            _html_kv("降级项", summary.get("degraded_count", 0)),
            _html_kv("已脱敏配置", summary.get("secret_redaction_count", 0)),
            "<p>预检不是 provider smoke；它不会访问 Tushare、CNINFO、新闻站点或社交来源。</p>",
            "</section>",
            _checks_table(_list(payload.get("checks"))),
            _list_section("安全命令", _list(payload.get("safe_commands"))),
            _list_section("Runbook", _list(payload.get("runbooks"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def build_release_manifest(
    *,
    output_dir: Path,
    preflight: dict[str, Any],
    mode: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    expected_artifacts = [
        _expected_artifact("product_home_html", "index.html", output_dir / "index.html"),
        _expected_artifact("artifact_browser_html", "artifact_browser.html", output_dir / "artifact_browser.html"),
        _expected_artifact("route_registry_json", "route_registry.json", output_dir / "route_registry.json"),
        _expected_artifact("route_registry_html", "route_registry.html", output_dir / "route_registry.html"),
        _expected_artifact("artifact_index_json", "artifact_index.json", output_dir / "artifact_index.json"),
        _expected_artifact("artifact_index_html", "artifact_index.html", output_dir / "artifact_index.html"),
        _expected_artifact("narrative_data_json", "narrative_data.json", output_dir / "narrative_data.json"),
        _expected_artifact("narrative_data_html", "narrative_data.html", output_dir / "narrative_data.html"),
        _expected_artifact("config_preflight_json", "config_preflight.json", output_dir / "config_preflight.json"),
        _expected_artifact("config_preflight_html", "config_preflight.html", output_dir / "config_preflight.html"),
        _expected_artifact(
            "source_quality_dashboard_json",
            "source_quality_dashboard.json",
            output_dir / "source_quality_dashboard.json",
        ),
        _expected_artifact(
            "source_quality_dashboard_html",
            "source_quality_dashboard.html",
            output_dir / "source_quality_dashboard.html",
        ),
        _expected_artifact("release_manifest_json", "release_manifest.json", output_dir / "release_manifest.json", planned=True),
        _expected_artifact("release_manifest_html", "release_manifest.html", output_dir / "release_manifest.html", planned=True),
        _expected_artifact(
            "acceptance_checklist_json",
            "acceptance_checklist.json",
            output_dir / "acceptance_checklist.json",
            planned=True,
        ),
        _expected_artifact(
            "acceptance_checklist_html",
            "acceptance_checklist.html",
            output_dir / "acceptance_checklist.html",
            planned=True,
        ),
    ]
    missing_count = sum(1 for artifact in expected_artifacts if not artifact["exists"])
    preflight_status = str(preflight.get("status") or "unknown")
    return {
        "version": "product-shell-release-manifest-v1",
        "generated_at": generated_at or _utc_now(),
        "mode": mode,
        "status": "degraded" if preflight_status == "degraded" or missing_count else "ok",
        "summary": {
            "expected_artifact_count": len(expected_artifacts),
            "missing_expected_artifact_count": missing_count,
            "preflight_status": preflight_status,
        },
        "commands": {
            "build_shell": "uv run python scripts/build_product_shell.py --output-dir outputs/product_shell/round8-current",
            "release_check": _validation_command(mode),
        },
        "startup_order": _list(preflight.get("startup_order")),
        "expected_artifacts": expected_artifacts,
        "preflight": {
            "status": preflight_status,
            "degraded_count": _mapping(preflight.get("summary")).get("degraded_count", 0),
            "provider_smoke_executed": _mapping(preflight.get("summary")).get("provider_smoke_executed", False),
        },
    }


def render_release_manifest_html(manifest: dict[str, Any]) -> str:
    summary = _mapping(manifest.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>本地发布包 Manifest</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>本地发布包 Manifest</h1>",
            '<section class="summary">',
            _html_kv("模式", manifest.get("mode")),
            _html_kv("状态", manifest.get("status")),
            _html_kv("预期产物", summary.get("expected_artifact_count", 0)),
            _html_kv("缺失产物", summary.get("missing_expected_artifact_count", 0)),
            "</section>",
            _artifact_table(_list(manifest.get("expected_artifacts"))),
            _list_section("命令", list(_mapping(manifest.get("commands")).values())),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def build_acceptance_checklist(
    *,
    manifest: dict[str, Any],
    preflight: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    artifact_ids = {
        str(artifact.get("artifact_id")): bool(artifact.get("exists"))
        for artifact in _list(manifest.get("expected_artifacts"))
        if isinstance(artifact, dict)
    }
    checks = [
        _acceptance_check(
            "product_shell_opens",
            artifact_ids.get("product_home_html", False),
            "fund-narrative-intelligence product shell",
            "产品首页可打开。",
        ),
        _acceptance_check(
            "major_routes_render",
            artifact_ids.get("route_registry_html", False)
            and artifact_ids.get("narrative_data_html", False)
            and artifact_ids.get("config_preflight_html", False),
            "FNI product shell",
            "主要路由有生成数据或预检产物。",
        ),
        _acceptance_check(
            "artifact_browser_links",
            artifact_ids.get("artifact_browser_html", False)
            and artifact_ids.get("artifact_index_json", False),
            "FNI artifact browser",
            "产物浏览器和索引均已生成。",
        ),
        _acceptance_check(
            "config_preflight_redacts_secrets",
            _mapping(preflight.get("summary")).get("provider_smoke_executed") is False,
            "FNI config preflight",
            "配置预检已生成，且不会执行 provider smoke。",
        ),
        _acceptance_check(
            "release_manifest_generated",
            artifact_ids.get("release_manifest_json", False)
            and artifact_ids.get("release_manifest_html", False),
            "FNI release package",
            "发布 manifest 已生成。",
        ),
    ]
    checks.extend(_service_acceptance_checks(preflight))
    failed_count = sum(1 for check in checks if check.get("status") == "fail")
    return {
        "version": "product-shell-acceptance-checklist-v1",
        "generated_at": generated_at or _utc_now(),
        "status": "fail" if failed_count else "pass",
        "summary": {
            "check_count": len(checks),
            "failed_count": failed_count,
        },
        "checks": checks,
    }


def render_acceptance_checklist_html(checklist: dict[str, Any]) -> str:
    summary = _mapping(checklist.get("summary"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '<meta charset="utf-8" />',
            '<meta name="viewport" content="width=device-width, initial-scale=1" />',
            "<title>产品壳验收清单</title>",
            "<style>",
            _html_styles(),
            "</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            "<h1>产品壳验收清单</h1>",
            '<section class="summary">',
            _html_kv("状态", checklist.get("status")),
            _html_kv("检查项", summary.get("check_count", 0)),
            _html_kv("失败项", summary.get("failed_count", 0)),
            "</section>",
            _acceptance_table(_list(checklist.get("checks"))),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _service_url_check(
    *,
    check_id: str,
    label: str,
    env_name: str,
    default_url: str,
    required: bool,
    env: Mapping[str, str],
) -> dict[str, Any]:
    raw_value = str(env.get(env_name) or "")
    if raw_value:
        status = "configured"
        value = raw_value
        message = "已配置本地服务 URL。"
    elif required:
        status = "missing"
        value = ""
        message = "live 模式需要显式配置本地服务 URL。"
    else:
        status = "optional_missing"
        value = default_url
        message = "demo 模式不要求服务已启动；展示默认本地 URL 作为启动提示。"
    return {
        "check_id": check_id,
        "label": label,
        "env_name": env_name,
        "status": status,
        "value": _redact_value(env_name, value),
        "required_in_demo": False,
        "required_in_live": required,
        "message": message,
    }


def _path_check(
    *,
    check_id: str,
    label: str,
    path: Path,
    project_root: Path,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "label": label,
        "status": "ok",
        "value": _safe_relative_path(path, project_root),
        "required_in_demo": True,
        "required_in_live": True,
        "message": "路径会由 release check 或 shell build 自动创建。",
    }


def _secret_checks(env: Mapping[str, str]) -> list[dict[str, Any]]:
    checks = []
    for name in sorted(env):
        if _is_secret_name(name) and env.get(name):
            checks.append(
                {
                    "check_id": f"redacted_{name.lower()}",
                    "label": name,
                    "env_name": name,
                    "status": "redacted",
                    "value": "***REDACTED***",
                    "required_in_demo": False,
                    "required_in_live": False,
                    "message": "检测到敏感配置，仅展示脱敏占位符。",
                }
            )
    return checks


def _startup_order() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "service": "stock-data-gateway",
            "required_in_demo": False,
            "required_in_live": True,
        },
        {
            "step": 2,
            "service": "stock-narrative-service",
            "required_in_demo": False,
            "required_in_live": True,
        },
        {
            "step": 3,
            "service": "fund-narrative-intelligence product shell",
            "required_in_demo": True,
            "required_in_live": True,
        },
    ]


def _validation_command(mode: str) -> str:
    return f"uv run python scripts/run_product_shell_release_check.py --mode {mode}"


def _redact_value(name: str, value: str) -> str:
    return "***REDACTED***" if _is_secret_name(name) and value else value


def _is_secret_name(name: str) -> bool:
    upper_name = name.upper()
    return any(marker in upper_name for marker in SECRET_MARKERS)


def _safe_relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return ""


def _checks_table(checks: list[Any]) -> str:
    rows = [_mapping(check) for check in checks]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("检查", "状态", "配置名", "值", "说明")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('label'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('env_name'))}</td>"
        f"<td>{_html_text(row.get('value'))}</td>"
        f"<td>{_html_text(row.get('message'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>检查结果</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _artifact_table(artifacts: list[Any]) -> str:
    rows = [_mapping(artifact) for artifact in artifacts]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("产物", "路径", "存在")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('artifact_id'))}</td>"
        f"<td>{_html_text(row.get('path'))}</td>"
        f"<td>{_html_text(row.get('exists'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>产物</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _acceptance_table(checks: list[Any]) -> str:
    rows = [_mapping(check) for check in checks]
    header = "".join(
        f"<th>{_html_text(label)}</th>"
        for label in ("检查", "状态", "责任面", "说明")
    )
    body = "".join(
        "<tr>"
        f"<td>{_html_text(row.get('check_id'))}</td>"
        f"<td>{_html_text(row.get('status'))}</td>"
        f"<td>{_html_text(row.get('responsible_surface'))}</td>"
        f"<td>{_html_text(row.get('message'))}</td>"
        "</tr>"
        for row in rows
    )
    return f"<section><h2>验收项</h2><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></section>"


def _expected_artifact(
    artifact_id: str,
    relative_path: str,
    path: Path,
    *,
    planned: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "path": relative_path,
        "exists": planned or path.exists(),
    }


def _acceptance_check(
    check_id: str,
    passed: bool,
    responsible_surface: str,
    message: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "responsible_surface": responsible_surface,
        "message": message,
    }


def _service_acceptance_checks(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    responsible_by_check_id = {
        "market_data_gateway_url": "stock-data-gateway",
        "narrative_service_url": "stock-narrative-service",
    }
    for item in _list(preflight.get("checks")):
        check = _mapping(item)
        responsible = responsible_by_check_id.get(str(check.get("check_id")))
        if responsible and check.get("status") == "missing":
            checks.append(
                _acceptance_check(
                    str(check.get("check_id")),
                    False,
                    responsible,
                    str(check.get("message") or "缺少服务配置。"),
                )
            )
    return checks


def _list_section(title: str, values: list[Any]) -> str:
    items = "".join(f"<li>{_html_text(value)}</li>" for value in values)
    return f"<section><h2>{_html_text(title)}</h2><ul>{items}</ul></section>"


def _html_kv(label: str, value: Any) -> str:
    return f"<p><strong>{_html_text(label)}:</strong> {_html_text(value)}</p>"


def _html_styles() -> str:
    return """
body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
h1 { font-size: 30px; margin: 0 0 16px; }
h2 { font-size: 20px; margin: 24px 0 12px; }
.summary { background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #e5eaf1; padding: 10px; text-align: left; vertical-align: top; font-size: 14px; }
th { background: #eef2f7; color: #323f4b; }
"""


def _html_text(value: Any) -> str:
    return escape(str(value or ""), quote=True)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
