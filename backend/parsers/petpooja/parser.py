"""Petpooja POS source parser."""

from __future__ import annotations

import logging

import pandas as pd

from backend.parsers.base import ParseResult, ParserDetection, SourceParser
from backend.parsers.column_mapper import map_columns
from backend.common.date_parser import parse_datetime_series
from backend.parsers.schemas import petpooja_schema as schema
from backend.parsers.schemas.canonical import (
    CANONICAL_AMOUNT,
    CANONICAL_COLUMNS,
    CANONICAL_DATE,
    CANONICAL_ORDER_ID,
    CANONICAL_OUTLET,
    CANONICAL_PLATFORM,
    CANONICAL_POS_INVOICE,
    CANONICAL_SOURCE_FILE,
    CANONICAL_STATUS,
    ROLE_TO_CANONICAL,
)

logger = logging.getLogger(__name__)


class PetpoojaParser(SourceParser):
    """Parse Petpooja Excel/CSV order reports into the canonical POS schema."""

    @property
    def parser_id(self) -> str:
        return schema.PLATFORM

    @property
    def platform(self) -> str:
        return schema.PLATFORM

    @property
    def source(self) -> str:
        return schema.SOURCE

    @property
    def currency(self) -> str:
        return schema.DEFAULT_CURRENCY

    def required_roles(self) -> tuple[str, ...]:
        return schema.REQUIRED_ROLES

    def detect(self, df: pd.DataFrame, filename: str | None = None) -> ParserDetection:
        reasons: list[str] = []
        column_map = map_columns(
            df.columns,
            aliases=schema.COLUMN_ALIASES,
            preferred_exact=schema.PREFERRED_EXACT,
        )
        missing = [role for role in schema.REQUIRED_ROLES if role not in column_map.values()]
        if missing:
            reasons.append(f"Missing required roles: {', '.join(missing)}")

        filename_hint = False
        if filename:
            lower = filename.lower()
            if any(hint in lower for hint in schema.FILENAME_HINTS):
                filename_hint = True
                reasons.append("Filename matches Petpooja naming hints")

        mapped_required = len(schema.REQUIRED_ROLES) - len(missing)
        confidence = mapped_required / len(schema.REQUIRED_ROLES)
        if filename_hint:
            confidence = min(1.0, confidence + 0.1)

        matched = len(missing) == 0
        if matched:
            reasons.append("All required Petpooja columns detected by name")

        return ParserDetection(
            matched=matched,
            platform=self.platform,
            source=self.source,
            column_map=column_map,
            confidence=confidence,
            reasons=tuple(reasons),
            currency=self.currency,
        )

    def parse(
        self,
        df: pd.DataFrame,
        column_map: dict[str, str],
        *,
        source_file: str,
    ) -> ParseResult:
        rename = {
            source: ROLE_TO_CANONICAL[role]
            for source, role in column_map.items()
            if role in ROLE_TO_CANONICAL
        }
        working = df.rename(columns=rename).copy()
        present = [c for c in CANONICAL_COLUMNS if c in working.columns]
        working = working[present].copy()
        working[CANONICAL_SOURCE_FILE] = source_file

        null_order_ids = 0
        null_amounts = 0

        if CANONICAL_ORDER_ID in working.columns:
            working[CANONICAL_ORDER_ID] = self._clean_order_id(working[CANONICAL_ORDER_ID])
            invalid = (
                working[CANONICAL_ORDER_ID].isna()
                | (working[CANONICAL_ORDER_ID].astype(str).str.len() == 0)
                | working[CANONICAL_ORDER_ID].isin(["nan", "None", "NaT", "#REF!"])
            )
            null_order_ids = int(invalid.sum())
            before = len(working)
            working = working.loc[~invalid].copy()
            dropped = before - len(working)
            if dropped:
                logger.info(
                    "Dropped rows without valid order id",
                    extra={
                        "context": {
                            "source_file": source_file,
                            "dropped": dropped,
                            "parser": self.parser_id,
                        }
                    },
                )

        if CANONICAL_AMOUNT in working.columns:
            amounts = pd.to_numeric(working[CANONICAL_AMOUNT], errors="coerce")
            null_amounts = int(amounts.isna().sum())
            # Preserve Sprint-1 behaviour: coerce null amounts to 0.0
            working[CANONICAL_AMOUNT] = amounts.fillna(0.0)
        if CANONICAL_DATE in working.columns:
            working[CANONICAL_DATE] = parse_datetime_series(working[CANONICAL_DATE])

        for col in (CANONICAL_OUTLET, CANONICAL_PLATFORM, CANONICAL_STATUS, CANONICAL_POS_INVOICE):
            if col in working.columns:
                working[col] = working[col].astype(str).str.strip()
                working[col] = working[col].replace(
                    {"nan": pd.NA, "None": pd.NA, "NaT": pd.NA, "<NA>": pd.NA}
                )

        for col in CANONICAL_COLUMNS:
            if col not in working.columns:
                working[col] = pd.NA
        working = working[list(CANONICAL_COLUMNS)].reset_index(drop=True)

        return ParseResult(
            dataframe=working,
            null_order_ids=null_order_ids,
            null_amounts=null_amounts,
            platform=self.platform,
            source=self.source,
            currency=self.currency,
        )

    @staticmethod
    def is_cancelled(status: object) -> bool:
        if status is None or (isinstance(status, float) and pd.isna(status)):
            return False
        text = str(status).strip().lower()
        return any(token in text for token in schema.CANCELLED_STATUS_TOKENS)

    def cancelled_mask(self, df: pd.DataFrame) -> pd.Series:
        if CANONICAL_STATUS not in df.columns or df.empty:
            return pd.Series(False, index=df.index)
        return df[CANONICAL_STATUS].map(self.is_cancelled)

    @staticmethod
    def _clean_order_id(series: pd.Series) -> pd.Series:
        return (
            series.astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .replace({"nan": "", "None": "", "NaT": "", "<NA>": ""})
        )
