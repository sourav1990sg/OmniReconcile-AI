"""Swiggy settlement parser — Pandas is private to this module."""

from __future__ import annotations

import io
import logging
from datetime import date
from decimal import Decimal

import pandas as pd

from backend.ingestion.logging_utils import log_with_context
from backend.parsers._money import clean_order_id, parse_date, to_decimal
from backend.parsers.base import ParserDetection
from backend.parsers.canonical import CanonicalDataset, CanonicalOrder, ValidationIssue
from backend.parsers.column_mapper import map_columns
from backend.parsers.settlement_base import SettlementParseResult, SettlementParser
from backend.parsers.swiggy import schema

logger = logging.getLogger(__name__)


class SwiggySettlementParser(SettlementParser):
    """Parse Swiggy annexure / settlement CSV (or Excel) into CanonicalDataset."""

    def __init__(self, *, reference_date: date | None = None) -> None:
        self._reference_date = reference_date

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

    def detect(self, filename: str, content: bytes) -> ParserDetection:
        reasons: list[str] = []
        lower = (filename or "").lower()
        filename_hint = any(h in lower for h in schema.FILENAME_HINTS)
        if filename_hint:
            reasons.append("Filename matches Swiggy settlement hints")

        try:
            df = self._load(filename, content)
        except Exception as exc:  # noqa: BLE001
            return ParserDetection(
                matched=False,
                platform=self.platform,
                source=self.source,
                column_map={},
                confidence=0.0,
                reasons=(f"Unreadable file: {exc}",),
                currency=self.currency,
            )

        column_map = map_columns(
            df.columns,
            aliases=schema.COLUMN_ALIASES,
            preferred_exact=schema.PREFERRED_EXACT,
        )
        missing = [r for r in schema.REQUIRED_ROLES if r not in column_map.values()]
        if missing:
            reasons.append(f"Missing required roles: {', '.join(missing)}")

        mapped = len(schema.REQUIRED_ROLES) - len(missing)
        confidence = mapped / len(schema.REQUIRED_ROLES)
        if filename_hint:
            confidence = min(1.0, confidence + 0.15)

        matched = len(missing) == 0
        if matched:
            reasons.append("All required Swiggy settlement columns detected")

        return ParserDetection(
            matched=matched,
            platform=self.platform,
            source=self.source,
            column_map=column_map,
            confidence=confidence,
            reasons=tuple(reasons),
            currency=self.currency,
        )

    def parse(self, filename: str, content: bytes) -> SettlementParseResult:
        detection = self.detect(filename, content)
        issues: list[ValidationIssue] = []

        if not detection.matched:
            issues.append(
                ValidationIssue(
                    code="missing_required_columns",
                    message="; ".join(detection.reasons) or "Not a Swiggy settlement report",
                    filename=filename,
                )
            )
            return SettlementParseResult(
                dataset=CanonicalDataset.empty(
                    platform=self.platform, source=self.source, currency=self.currency
                ),
                detection=detection,
                issues=issues,
                is_valid=False,
            )

        try:
            df = self._load(filename, content)
        except Exception as exc:  # noqa: BLE001
            issues.append(
                ValidationIssue(
                    code="unreadable_file",
                    message=str(exc),
                    filename=filename,
                )
            )
            return SettlementParseResult(
                dataset=CanonicalDataset.empty(
                    platform=self.platform, source=self.source, currency=self.currency
                ),
                detection=detection,
                issues=issues,
                is_valid=False,
            )

        if df.empty:
            issues.append(
                ValidationIssue(
                    code="empty_file",
                    message="File contains no data rows",
                    filename=filename,
                )
            )
            return SettlementParseResult(
                dataset=CanonicalDataset.empty(
                    platform=self.platform, source=self.source, currency=self.currency
                ),
                detection=detection,
                issues=issues,
                rows_read=0,
                is_valid=False,
            )

        return self._normalize(df, detection, filename=filename)

    def _normalize(
        self,
        df: pd.DataFrame,
        detection: ParserDetection,
        *,
        filename: str,
    ) -> SettlementParseResult:
        role_cols = {role: src for src, role in detection.column_map.items()}
        id_col = role_cols["order_id"]
        amt_col = role_cols["settled_amount"]
        date_col = role_cols.get("date")
        status_col = role_cols.get("status")
        outlet_col = role_cols.get("outlet")

        orders: list[CanonicalOrder] = []
        null_order_ids = 0
        null_amounts = 0
        negative_amounts = 0
        future_dates = 0
        invalid_dates = 0
        issues: list[ValidationIssue] = []
        today = self._reference_date or date.today()
        seen_ids: dict[str, int] = {}

        for _, row in df.iterrows():
            oid = clean_order_id(row.get(id_col))
            if oid is None:
                null_order_ids += 1
                continue

            amount = to_decimal(row.get(amt_col))
            if amount is None:
                null_amounts += 1
                # Keep order with 0 for eligibility tracking? Spec: warn null settlement —
                # exclude from eligible but could still include. We'll skip from dataset
                # but count null_amounts (same as dropping incomplete settlements).
                continue

            if amount < Decimal("0"):
                negative_amounts += 1

            settlement_date = None
            if date_col:
                settlement_date = parse_date(row.get(date_col))
                if row.get(date_col) is not None and str(row.get(date_col)).strip() not in {
                    "",
                    "nan",
                    "None",
                }:
                    if settlement_date is None:
                        invalid_dates += 1
                if settlement_date is not None and settlement_date.date() > today:
                    future_dates += 1

            status = None
            if status_col and pd.notna(row.get(status_col)):
                status = str(row.get(status_col)).strip() or None

            outlet = None
            if outlet_col and pd.notna(row.get(outlet_col)):
                outlet = str(row.get(outlet_col)).strip() or None

            seen_ids[oid] = seen_ids.get(oid, 0) + 1
            orders.append(
                CanonicalOrder(
                    aggregator_order_id=oid,
                    settled_amount=amount,
                    settlement_date=settlement_date,
                    platform=self.platform,
                    source_file=filename,
                    outlet=outlet,
                    order_status=status,
                )
            )

        duplicate_order_ids = sum(1 for _oid, count in seen_ids.items() if count > 1)
        self._append_quality_issues(
            issues,
            filename=filename,
            null_order_ids=null_order_ids,
            null_amounts=null_amounts,
            negative_amounts=negative_amounts,
            future_dates=future_dates,
            invalid_dates=invalid_dates,
            duplicate_order_ids=duplicate_order_ids,
        )

        dataset = CanonicalDataset(
            platform=self.platform,
            source=self.source,
            currency=self.currency,
            orders=tuple(orders),
        )
        log_with_context(
            logger,
            logging.INFO,
            "Parsed Swiggy settlement file",
            filename=filename,
            rows_read=len(df),
            orders=len(orders),
            null_amounts=null_amounts,
            duplicate_order_ids=duplicate_order_ids,
        )
        return SettlementParseResult(
            dataset=dataset,
            detection=detection,
            issues=issues,
            rows_read=len(df),
            null_order_ids=null_order_ids,
            null_amounts=null_amounts,
            negative_amounts=negative_amounts,
            future_dates=future_dates,
            duplicate_order_ids=duplicate_order_ids,
            invalid_dates=invalid_dates,
            is_valid=True,
        )

    @staticmethod
    def _append_quality_issues(
        issues: list[ValidationIssue],
        *,
        filename: str,
        null_order_ids: int,
        null_amounts: int,
        negative_amounts: int,
        future_dates: int,
        invalid_dates: int,
        duplicate_order_ids: int,
    ) -> None:
        if null_order_ids:
            issues.append(
                ValidationIssue(
                    code="null_order_ids",
                    message=f"{null_order_ids} row(s) missing Order No",
                    filename=filename,
                    severity="warning",
                )
            )
        if null_amounts:
            issues.append(
                ValidationIssue(
                    code="null_settlement_amount",
                    message=f"{null_amounts} row(s) missing settlement amount",
                    filename=filename,
                    severity="warning",
                )
            )
        if negative_amounts:
            issues.append(
                ValidationIssue(
                    code="negative_settlement_amount",
                    message=f"{negative_amounts} row(s) have negative settlement amount",
                    filename=filename,
                    severity="warning",
                )
            )
        if future_dates:
            issues.append(
                ValidationIssue(
                    code="future_settlement_date",
                    message=f"{future_dates} row(s) have future settlement/order dates",
                    filename=filename,
                    severity="warning",
                )
            )
        if invalid_dates:
            issues.append(
                ValidationIssue(
                    code="invalid_dates",
                    message=f"{invalid_dates} row(s) have invalid dates",
                    filename=filename,
                    severity="warning",
                )
            )
        if duplicate_order_ids:
            issues.append(
                ValidationIssue(
                    code="duplicate_order_ids",
                    message=f"{duplicate_order_ids} distinct Order No value(s) appear more than once",
                    filename=filename,
                    severity="warning",
                )
            )

    @staticmethod
    def _load(filename: str, content: bytes) -> pd.DataFrame:
        lower = (filename or "").lower()
        buf = io.BytesIO(content)
        if lower.endswith(".csv"):
            return pd.read_csv(buf)
        if lower.endswith((".xlsx", ".xls", ".xlsm")):
            return pd.read_excel(buf, engine="openpyxl")
        # Attempt CSV for annexure files without extension quirks
        try:
            return pd.read_csv(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Unsupported Swiggy file type for '{filename}'") from exc
