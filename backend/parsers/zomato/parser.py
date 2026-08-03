"""Zomato settlement parser — Pandas is private to this module."""

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
from backend.parsers.zomato import schema

logger = logging.getLogger(__name__)


class ZomatoSettlementParser(SettlementParser):
    """Parse Zomato Order Level settlement workbooks into CanonicalDataset."""

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
            reasons.append("Filename matches Zomato settlement hints")

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
        # Prefer Order level Payout over ambiguous 'payout' hits on GST columns
        column_map = self._prefer_payout_column(df.columns, column_map)

        missing = [r for r in schema.REQUIRED_ROLES if r not in column_map.values()]
        if missing:
            reasons.append(f"Missing required roles: {', '.join(missing)}")

        mapped = len(schema.REQUIRED_ROLES) - len(missing)
        confidence = mapped / len(schema.REQUIRED_ROLES)
        if filename_hint:
            confidence = min(1.0, confidence + 0.15)

        matched = len(missing) == 0
        if matched:
            reasons.append("All required Zomato settlement columns detected")

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
                    message="; ".join(detection.reasons) or "Not a Zomato settlement report",
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
                ValidationIssue(code="unreadable_file", message=str(exc), filename=filename)
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
                continue

            if amount < Decimal("0"):
                negative_amounts += 1

            settlement_date = None
            if date_col:
                raw_date = row.get(date_col)
                settlement_date = parse_date(raw_date)
                if raw_date is not None and str(raw_date).strip() not in {"", "nan", "None"}:
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
        if null_order_ids:
            issues.append(
                ValidationIssue(
                    code="null_order_ids",
                    message=f"{null_order_ids} row(s) missing/invalid Order ID (incl. #REF!)",
                    filename=filename,
                    severity="warning",
                )
            )
        if null_amounts:
            issues.append(
                ValidationIssue(
                    code="null_settlement_amount",
                    message=f"{null_amounts} row(s) missing Order level Payout",
                    filename=filename,
                    severity="warning",
                )
            )
        if negative_amounts:
            issues.append(
                ValidationIssue(
                    code="negative_settlement_amount",
                    message=f"{negative_amounts} row(s) have negative payout",
                    filename=filename,
                    severity="warning",
                )
            )
        if future_dates:
            issues.append(
                ValidationIssue(
                    code="future_settlement_date",
                    message=f"{future_dates} row(s) have future dates",
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
                    message=f"{duplicate_order_ids} distinct Order ID value(s) appear more than once",
                    filename=filename,
                    severity="warning",
                )
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
            "Parsed Zomato settlement file",
            filename=filename,
            rows_read=len(df),
            orders=len(orders),
            null_order_ids=null_order_ids,
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
    def _prefer_payout_column(
        columns: pd.Index,
        column_map: dict[str, str],
    ) -> dict[str, str]:
        """Ensure settled_amount maps to Order level Payout / Net Payout by name."""
        payout_cols = [
            c
            for c in columns
            if "order level payout" in str(c).lower() or "net payout" in str(c).lower()
        ]
        if not payout_cols:
            return column_map
        # Prefer explicit Order level Payout
        preferred = next(
            (c for c in payout_cols if "order level payout" in str(c).lower()),
            payout_cols[0],
        )
        # Remove prior settled_amount mapping
        column_map = {src: role for src, role in column_map.items() if role != "settled_amount"}
        column_map[str(preferred)] = "settled_amount"
        return column_map

    def _load(self, filename: str, content: bytes) -> pd.DataFrame:
        lower = (filename or "").lower()
        if not lower.endswith((".xlsx", ".xls", ".xlsm")):
            raise ValueError(f"Zomato settlements require Excel files, got '{filename}'")

        # Discover header row by column names (never hardcode index)
        preview = pd.read_excel(
            io.BytesIO(content),
            sheet_name=schema.ORDER_LEVEL_SHEET,
            header=None,
            nrows=30,
            engine="openpyxl",
        )
        header_idx: int | None = None
        for idx, row in preview.iterrows():
            values = [str(v) for v in row.tolist() if pd.notna(v)]
            probe = pd.DataFrame(columns=values)
            mapped = map_columns(
                probe.columns,
                aliases=schema.COLUMN_ALIASES,
                preferred_exact=schema.PREFERRED_EXACT,
            )
            if "order_id" in mapped.values() and (
                any("order level payout" in str(v).lower() for v in values)
                or any("net payout" in str(v).lower() for v in values)
                or "settled_amount" in mapped.values()
            ):
                header_idx = int(idx)
                break
            if any("Order ID" == v for v in values):
                header_idx = int(idx)
                break

        if header_idx is None:
            header_idx = 0

        return pd.read_excel(
            io.BytesIO(content),
            sheet_name=schema.ORDER_LEVEL_SHEET,
            header=header_idx,
            engine="openpyxl",
        )
