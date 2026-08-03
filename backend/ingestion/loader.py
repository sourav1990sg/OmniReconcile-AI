"""Generic spreadsheet file loader (parser-agnostic)."""

from __future__ import annotations

import io
import logging
from typing import Callable

import pandas as pd

from backend.ingestion.logging_utils import log_with_context

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".xlsx", ".xls", ".xlsm", ".csv")


class FileLoader:
    """
    Load uploaded bytes into a raw DataFrame.

    Does not interpret business columns — that is the parser's job.
    """

    def is_supported_filename(self, filename: str | None) -> bool:
        if not filename:
            return False
        lower = filename.lower()
        return any(lower.endswith(ext) for ext in SUPPORTED_EXTENSIONS)

    def load(self, filename: str, content: bytes) -> pd.DataFrame:
        """Read CSV/Excel content into a DataFrame using pandas defaults."""
        lower = (filename or "").lower()
        buffer = io.BytesIO(content)

        if lower.endswith(".csv"):
            df = pd.read_csv(buffer)
        elif lower.endswith((".xlsx", ".xls", ".xlsm")):
            engine = "openpyxl" if lower.endswith((".xlsx", ".xlsm")) else None
            df = pd.read_excel(buffer, engine=engine)
        else:
            raise ValueError(f"Unsupported file type for '{filename}'")

        log_with_context(
            logger,
            logging.DEBUG,
            "Loaded spreadsheet",
            filename=filename,
            rows=len(df),
            columns=len(df.columns),
        )
        return df

    def discover_header_frame(
        self,
        content: bytes,
        filename: str,
        *,
        is_match: Callable[[pd.DataFrame, str], bool],
    ) -> pd.DataFrame | None:
        """
        Scan early Excel rows for a header that satisfies ``is_match``.

        Row selection is driven by column **names** via the callback — no
        hardcoded header index.
        """
        lower = (filename or "").lower()
        if not lower.endswith((".xlsx", ".xls", ".xlsm")):
            return None
        try:
            preview = pd.read_excel(io.BytesIO(content), header=None, nrows=30, engine="openpyxl")
        except Exception:  # noqa: BLE001
            return None

        for idx, row in preview.iterrows():
            values = [str(v) for v in row.tolist() if pd.notna(v)]
            probe = pd.DataFrame(columns=values)
            if is_match(probe, filename):
                log_with_context(
                    logger,
                    logging.INFO,
                    "Discovered header row by column names",
                    filename=filename,
                    header_index=int(idx),
                )
                return pd.read_excel(io.BytesIO(content), header=int(idx), engine="openpyxl")
        return None
