from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_artifact(payload: dict[str, Any], path: Path) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path
