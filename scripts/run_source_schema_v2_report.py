from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.scanners.source_schema_v2 import build_source_schema_v2_report  # noqa: E402

OUTPUT_STEM = "source_schema_v2_report"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the narrative source schema v2 report.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR / "source_schema_v2" / "current",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_source_schema_v2_report()
    write_outputs(args.output_dir, report)
    return 0


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{OUTPUT_STEM}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{OUTPUT_STEM}.html").write_text(
        render_html(report),
        encoding="utf-8",
    )


def render_html(report: dict[str, Any]) -> str:
    rows = "\n".join(_entity_rows(report.get("entities")))
    classes = ", ".join(report.get("supported_source_classes") or [])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>叙事来源 Schema v2 报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; }}
    .meta {{ color: #4b5563; line-height: 1.6; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: 13px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>叙事来源 Schema v2 报告</h1>
  <div class="meta">
    <div>Schema：<code>{html.escape(report["schema_version"])}</code></div>
    <div>来源类型：{html.escape(classes)}</div>
    <div>raw_content_policy：{html.escape(json.dumps(report.get("raw_content_policy_contract"), ensure_ascii=False))}</div>
  </div>
  <table>
    <thead><tr><th>实体</th><th>必填字段</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def _entity_rows(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    rows = []
    for name, spec in value.items():
        fields = spec.get("required_fields") if isinstance(spec, dict) else []
        rows.append(
            "      <tr>"
            f"<td><code>{html.escape(str(name))}</code></td>"
            f"<td>{html.escape(', '.join(str(field) for field in fields))}</td>"
            "</tr>"
        )
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
