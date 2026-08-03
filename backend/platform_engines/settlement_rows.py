"""
Load settlement financial rows by Order ID from upload bytes.

Does not modify settlement ingestion — independent column-name reader for engines.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Mapping, Sequence

import pandas as pd

from backend.ingestion.logging_utils import log_with_context
from backend.parsers.column_mapper import map_columns, normalize_header
from backend.parsers.swiggy import schema as swiggy_schema
from backend.parsers.zomato import schema as zomato_schema
from backend.parsers.zomato.parser import ZomatoSettlementParser

logger = logging.getLogger(__name__)


def _clean_oid(value: object) -> str:
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>", "#ref!"}:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text


class SettlementFinancialIndex:
    """
    order_id → {platform, source_file, row: dict[column→value]}.

    Built from raw settlement upload bytes using schema aliases only.
    """

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def __len__(self) -> int:
        return len(self._rows)

    def get(self, order_id: str) -> dict[str, Any] | None:
        return self._rows.get(str(order_id).strip())

    def load_files(self, files: Sequence[tuple[str, bytes]]) -> "SettlementFinancialIndex":
        for name, content in files:
            lower = (name or "").lower()
            try:
                if lower.endswith(".csv") or "swiggy" in lower or "annexure" in lower:
                    self._ingest_swiggy(name, content)
                elif lower.endswith((".xlsx", ".xls", ".xlsm")):
                    # Try Zomato Order Level; if that fails try Swiggy excel
                    if self._ingest_zomato(name, content) == 0:
                        self._ingest_swiggy_excel(name, content)
                else:
                    self._ingest_swiggy(name, content)
            except Exception as exc:  # noqa: BLE001
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Financial index failed for file",
                    filename=name,
                    error=str(exc),
                )
        return self

    def _ingest_swiggy(self, filename: str, content: bytes) -> int:
        df = pd.read_csv(io.BytesIO(content))
        return self._index_frame(df, filename=filename, platform="swiggy", schema=swiggy_schema)

    def _ingest_swiggy_excel(self, filename: str, content: bytes) -> int:
        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        return self._index_frame(df, filename=filename, platform="swiggy", schema=swiggy_schema)

    def _ingest_zomato(self, filename: str, content: bytes) -> int:
        try:
            df = ZomatoSettlementParser()._load(filename, content)
        except Exception:  # noqa: BLE001
            return 0
        return self._index_frame(df, filename=filename, platform="zomato", schema=zomato_schema)

    def _index_frame(
        self,
        df: pd.DataFrame,
        *,
        filename: str,
        platform: str,
        schema: Any,
    ) -> int:
        cmap = map_columns(
            df.columns,
            aliases=schema.COLUMN_ALIASES,
            preferred_exact=getattr(schema, "PREFERRED_EXACT", None),
        )
        role = {r: s for s, r in cmap.items()}
        oid_col = role.get("order_id")
        if not oid_col:
            return 0
        count = 0
        for _, series in df.iterrows():
            oid = _clean_oid(series.get(oid_col))
            if not oid:
                continue
            # Skip spreadsheet error rows
            if any(str(series.get(c)).strip() == "#REF!" for c in df.columns[:3]):
                continue
            row_dict = {str(c): series.get(c) for c in df.columns}
            # First wins (FIFO) — matches reconciliation matcher
            if oid not in self._rows:
                self._rows[oid] = {
                    "platform": platform,
                    "source_file": filename,
                    "row": row_dict,
                }
                count += 1
        log_with_context(
            logger,
            logging.INFO,
            "Indexed settlement financial rows",
            filename=filename,
            platform=platform,
            indexed=count,
        )
        return count
