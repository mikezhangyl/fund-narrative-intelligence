from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT


class ParquetStore:
    def __init__(self, root_dir: Path | str | None = None):
        self.root_dir = Path(root_dir or PROJECT_ROOT / "data" / "cache" / "parquet")

    def write_rows(
        self,
        *,
        dataset: str,
        rows: list[dict[str, Any]],
    ) -> Path:
        try:
            return self._write_parquet(dataset=dataset, rows=rows)
        except ImportError:
            return self._write_csv_fallback(dataset=dataset, rows=rows)

    def _write_parquet(self, *, dataset: str, rows: list[dict[str, Any]]) -> Path:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore

        path = self.root_dir / f"{dataset}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows), path)
        return path

    def _write_csv_fallback(self, *, dataset: str, rows: list[dict[str, Any]]) -> Path:
        path = self.root_dir / f"{dataset}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({field for row in rows for field in row})
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path
