from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVICE_SRC = PROJECT_ROOT / "services" / "stock-narrative-service" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from stock_narrative_service.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

