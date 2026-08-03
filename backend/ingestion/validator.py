"""
Parser-agnostic validation for ingested POS datasets.

Fatal issues block a file/dataset; quality issues are warnings that do not
stop ingestion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

import pandas as pd

from backend.common.date_parser import parse_datetime_series
from backend.ingestion.detector import DetectionResult
from backend.ingestion.logging_utils import log_with_context
from backend.ingestion.models import ValidationIssue
from backend.parsers.schemas.canonical import (
    CANONICAL_AMOUNT,
    CANONICAL_DATE,
    CANONICAL_ORDER_ID,
    CANONICAL_POS_INVOICE,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Aggregate validation outcome for one file or a merged frame."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def extend(self, other: ValidationResult) -> None:
        self.issues.extend(other.issues)
        self.is_valid = self.is_valid and other.is_valid


@dataclass
class QualityMetrics:
    """Counts produced while validating a canonical dataset."""

    duplicate_aggregator_orders: int = 0
    duplicate_invoice_numbers: int = 0
    null_order_ids: int = 0
    null_amounts: int = 0
    future_dates: int = 0
    negative_amounts: int = 0


class DatasetValidator:
    """
    Validate raw uploads and canonical datasets.

    Warnings never flip ``is_valid`` to False; only ``severity='error'`` does.
    """

    def __init__(
        self,
        *,
        reference_date: date | None = None,
        required_roles_provider: Callable[[DetectionResult], tuple[str, ...]] | None = None,
    ) -> None:
        self._reference_date = reference_date
        self._required_roles_provider = required_roles_provider

    def validate_file(
        self,
        df: pd.DataFrame,
        *,
        filename: str,
        detection: DetectionResult,
    ) -> ValidationResult:
        """Run per-file checks before routing to a parser."""
        issues: list[ValidationIssue] = []

        if df is None or df.empty:
            issues.append(
                ValidationIssue(
                    code="empty_file",
                    message="File contains no data rows",
                    filename=filename,
                )
            )
            return ValidationResult(is_valid=False, issues=issues)

        if not detection.matched:
            issues.append(
                ValidationIssue(
                    code="invalid_file",
                    message=(
                        "Unsupported or unrecognized report: "
                        + ("; ".join(detection.reasons) or "required columns missing")
                    ),
                    filename=filename,
                )
            )
            return ValidationResult(is_valid=False, issues=issues)

        # Sprint-1 wording compatibility for Petpooja
        if detection.is_petpooja is False and detection.matched is False:
            pass  # already handled

        required = self._required_roles(detection)
        missing_roles = [role for role in required if role not in detection.column_map.values()]
        if missing_roles:
            issues.append(
                ValidationIssue(
                    code="missing_columns",
                    message=f"Missing required columns for roles: {', '.join(missing_roles)}",
                    filename=filename,
                )
            )

        date_source = next(
            (src for src, role in detection.column_map.items() if role == "date"),
            None,
        )
        if date_source and date_source in df.columns:
            parsed = parse_datetime_series(df[date_source])
            if parsed.notna().sum() == 0:
                issues.append(
                    ValidationIssue(
                        code="invalid_dates",
                        message=f"Column '{date_source}' has no parseable dates",
                        filename=filename,
                        severity="error",
                    )
                )
            elif parsed.isna().any():
                bad = int(parsed.isna().sum())
                issues.append(
                    ValidationIssue(
                        code="partial_invalid_dates",
                        message=f"{bad} row(s) have unparseable dates in '{date_source}'",
                        filename=filename,
                        severity="warning",
                    )
                )

        fatal = [i for i in issues if i.severity == "error"]
        is_valid = len(fatal) == 0
        log_with_context(
            logger,
            logging.INFO,
            "Validated file",
            filename=filename,
            valid=is_valid,
            issue_count=len(issues),
            platform=detection.platform,
        )
        return ValidationResult(is_valid=is_valid, issues=issues)

    def validate_merged(self, df: pd.DataFrame) -> ValidationResult:
        """Backward-compatible alias for :meth:`validate_dataset`."""
        result, _metrics = self.validate_dataset(df)
        return result

    def validate_dataset(
        self,
        df: pd.DataFrame,
        *,
        null_order_ids_from_parse: int = 0,
        null_amounts_from_parse: int = 0,
    ) -> tuple[ValidationResult, QualityMetrics]:
        """
        Validate the merged canonical dataset.

        Quality findings are warnings; an empty merge is a hard error.
        """
        issues: list[ValidationIssue] = []
        metrics = QualityMetrics(
            null_order_ids=null_order_ids_from_parse,
            null_amounts=null_amounts_from_parse,
        )

        if df is None or df.empty:
            issues.append(
                ValidationIssue(
                    code="empty_merge",
                    message="Merged POS dataset is empty",
                )
            )
            return ValidationResult(is_valid=False, issues=issues), metrics

        # --- duplicate aggregator order IDs ---
        if CANONICAL_ORDER_ID in df.columns:
            dup_mask = df[CANONICAL_ORDER_ID].duplicated(keep=False)
            dup_count = int(df.loc[dup_mask, CANONICAL_ORDER_ID].nunique())
            metrics.duplicate_aggregator_orders = dup_count
            if dup_count:
                issues.append(
                    ValidationIssue(
                        code="duplicate_aggregator_orders",
                        message=(
                            f"{dup_count} distinct Aggregator_Order_ID value(s) appear more than once"
                        ),
                        severity="warning",
                    )
                )
                # Sprint-1 code retained as alias warning
                issues.append(
                    ValidationIssue(
                        code="duplicate_orders",
                        message=(
                            f"{dup_count} distinct Aggregator_Order_ID value(s) appear more than once"
                        ),
                        severity="warning",
                    )
                )

        # --- duplicate invoice numbers ---
        if CANONICAL_POS_INVOICE in df.columns:
            invoices = df[CANONICAL_POS_INVOICE]
            valid_inv = invoices.notna() & ~invoices.astype(str).str.strip().isin(
                ["", "nan", "None", "<NA>", "NaT"]
            )
            dup_inv = invoices[valid_inv].duplicated(keep=False)
            dup_inv_count = int(invoices[valid_inv][dup_inv].nunique())
            metrics.duplicate_invoice_numbers = dup_inv_count
            if dup_inv_count:
                issues.append(
                    ValidationIssue(
                        code="duplicate_invoice_numbers",
                        message=(
                            f"{dup_inv_count} distinct POS invoice number(s) appear more than once"
                        ),
                        severity="warning",
                    )
                )

        # --- null order IDs (from parse drops + any remaining) ---
        if CANONICAL_ORDER_ID in df.columns:
            remaining_null = int(
                (
                    df[CANONICAL_ORDER_ID].isna()
                    | (df[CANONICAL_ORDER_ID].astype(str).str.len() == 0)
                ).sum()
            )
            metrics.null_order_ids = null_order_ids_from_parse + remaining_null
            if metrics.null_order_ids:
                issues.append(
                    ValidationIssue(
                        code="null_order_ids",
                        message=f"{metrics.null_order_ids} row(s) had null/empty Aggregator_Order_ID",
                        severity="warning",
                    )
                )

        # --- null expected amounts (captured at parse before fillna) ---
        if null_amounts_from_parse:
            metrics.null_amounts = null_amounts_from_parse
            issues.append(
                ValidationIssue(
                    code="null_amounts",
                    message=f"{null_amounts_from_parse} row(s) had null Expected_Amount (coerced to 0)",
                    severity="warning",
                )
            )
        elif CANONICAL_AMOUNT in df.columns:
            null_amt = int(pd.to_numeric(df[CANONICAL_AMOUNT], errors="coerce").isna().sum())
            metrics.null_amounts = null_amt
            if null_amt:
                issues.append(
                    ValidationIssue(
                        code="null_amounts",
                        message=f"{null_amt} row(s) have null Expected_Amount",
                        severity="warning",
                    )
                )

        # --- negative amounts ---
        if CANONICAL_AMOUNT in df.columns:
            amounts = pd.to_numeric(df[CANONICAL_AMOUNT], errors="coerce")
            neg = int((amounts < 0).sum())
            metrics.negative_amounts = neg
            if neg:
                issues.append(
                    ValidationIssue(
                        code="negative_amounts",
                        message=f"{neg} row(s) have negative Expected_Amount",
                        severity="warning",
                    )
                )

        # --- future order dates ---
        if CANONICAL_DATE in df.columns:
            dates = parse_datetime_series(df[CANONICAL_DATE])
            if dates.notna().any():
                today = self._reference_date or date.today()
                today_ts = pd.Timestamp(today)
                future_mask = dates.notna() & (dates.dt.normalize() > today_ts)
                future_count = int(future_mask.sum())
                metrics.future_dates = future_count
                if future_count:
                    issues.append(
                        ValidationIssue(
                            code="future_dates",
                            message=f"{future_count} row(s) have order dates after {today.isoformat()}",
                            severity="warning",
                        )
                    )
            else:
                issues.append(
                    ValidationIssue(
                        code="invalid_date_range",
                        message="Merged dataset has no valid dates",
                        severity="error",
                    )
                )

        fatal = [i for i in issues if i.severity == "error"]
        log_with_context(
            logger,
            logging.INFO,
            "Validated dataset",
            valid=len(fatal) == 0,
            warnings=sum(1 for i in issues if i.severity == "warning"),
            duplicate_aggregator_orders=metrics.duplicate_aggregator_orders,
            duplicate_invoice_numbers=metrics.duplicate_invoice_numbers,
            null_order_ids=metrics.null_order_ids,
            null_amounts=metrics.null_amounts,
            future_dates=metrics.future_dates,
            negative_amounts=metrics.negative_amounts,
        )
        return ValidationResult(is_valid=len(fatal) == 0, issues=issues), metrics

    def _required_roles(self, detection: DetectionResult) -> tuple[str, ...]:
        if self._required_roles_provider:
            return self._required_roles_provider(detection)
        return ("order_id", "amount", "date", "outlet")


# Sprint-1 compatible name
class PetpoojaReportValidator(DatasetValidator):
    """Backward-compatible validator alias."""

    def validate_file(
        self,
        df: pd.DataFrame,
        *,
        filename: str,
        detection: DetectionResult,
    ) -> ValidationResult:
        result = super().validate_file(df, filename=filename, detection=detection)
        # Preserve Sprint-1 message prefix for unrecognized files
        for issue in result.issues:
            if issue.code == "invalid_file" and issue.message.startswith("Unsupported"):
                issue.message = issue.message.replace(
                    "Unsupported or unrecognized report:",
                    "Not a Petpooja POS report:",
                    1,
                )
        return result
