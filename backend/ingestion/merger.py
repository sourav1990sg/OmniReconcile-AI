"""
Merge canonical frames from any parser.

Normalization / alias mapping lives in parsers; this module only concatenates
canonical DataFrames. ``PosReportMerger`` remains as a Sprint-1 facade that
delegates Petpooja normalization to :class:`PetpoojaParser`.
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

from backend.ingestion.logging_utils import log_with_context
from backend.parsers.petpooja import PetpoojaParser
from backend.parsers.schemas.canonical import (
    CANONICAL_COLUMNS,
    CANONICAL_DATE,
    CANONICAL_ORDER_ID,
    CANONICAL_STATUS,
)

logger = logging.getLogger(__name__)


class DatasetMerger:
    """Concatenate already-canonical POS frames."""

    def merge(self, frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
        frames_list = [f for f in frames if f is not None and not f.empty]
        if not frames_list:
            log_with_context(logger, logging.WARNING, "No frames to merge")
            return pd.DataFrame(columns=list(CANONICAL_COLUMNS))

        merged = pd.concat(frames_list, ignore_index=True)
        if CANONICAL_DATE in merged.columns:
            merged = merged.sort_values(
                by=[CANONICAL_DATE, CANONICAL_ORDER_ID],
                ascending=True,
                kind="mergesort",
            ).reset_index(drop=True)

        log_with_context(
            logger,
            logging.INFO,
            "Merged canonical frames",
            file_frames=len(frames_list),
            orders=len(merged),
        )
        return merged

    def duplicate_order_count(self, df: pd.DataFrame) -> int:
        if df.empty or CANONICAL_ORDER_ID not in df.columns:
            return 0
        duplicated_ids = df.loc[
            df[CANONICAL_ORDER_ID].duplicated(keep=False), CANONICAL_ORDER_ID
        ]
        return int(duplicated_ids.nunique())


class PosReportMerger(DatasetMerger):
    """
    Sprint-1 facade: Petpooja normalize + merge.

    Prefer routing through :class:`ParserRouter` in new code.
    """

    def __init__(self) -> None:
        self._parser = PetpoojaParser()

    def normalize(
        self,
        df: pd.DataFrame,
        column_map: dict[str, str],
        *,
        source_file: str,
    ) -> pd.DataFrame:
        """Delegate Petpooja mapping to the Petpooja parser."""
        return self._parser.parse(df, column_map, source_file=source_file).dataframe

    def is_cancelled(self, status: object) -> bool:
        return self._parser.is_cancelled(status)

    def cancelled_mask(self, df: pd.DataFrame) -> pd.Series:
        return self._parser.cancelled_mask(df)
