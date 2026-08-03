"""Upload validation findings (severity-tagged, never swallowed)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

import pandas as pd

from backend.common.date_parser import parse_datetime_series
from backend.parsers.column_mapper import normalize_header
from backend.upload_intelligence.models import (
    DatasetRole,
    FilePreview,
    PlatformKind,
    Severity,
    ValidationFinding,
)
from backend.upload_intelligence.profiles import DetectionProfile, build_profiles


class UploadValidator:
    """
    Validate detected upload frames before commit.

    Does not raise for soft issues — always returns findings with severity.
    """

    def __init__(
        self,
        *,
        reference_date: date | None = None,
        expected_currency: str = "INR",
    ) -> None:
        self._as_of = reference_date or date.today()
        self._expected_currency = expected_currency
        self._profiles = {p.platform: p for p in build_profiles()}

    def validate_frame(
        self,
        *,
        filename: str,
        platform: PlatformKind,
        column_map: dict[str, str],
        df: pd.DataFrame,
        currency: str,
        load_error: str | None = None,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        if load_error:
            findings.append(
                ValidationFinding(
                    code="unreadable_file",
                    message=f"Unreadable file: {load_error}",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return findings

        if df is None or (len(df) == 0 and not list(df.columns)):
            findings.append(
                ValidationFinding(
                    code="empty_file",
                    message="Empty file",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return findings

        if len(df) == 0:
            findings.append(
                ValidationFinding(
                    code="empty_file",
                    message="File has headers but zero data rows",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )

        profile = self._profiles.get(platform)
        if profile is None or platform == PlatformKind.UNKNOWN:
            findings.append(
                ValidationFinding(
                    code="unknown_file",
                    message="UNKNOWN_FILE — missing required schema match",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return findings

        roles = set(column_map.values())
        missing = [r for r in profile.required_roles if r not in roles]
        if missing:
            findings.append(
                ValidationFinding(
                    code="missing_required_columns",
                    message=f"Missing required columns: {', '.join(missing)}",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )

        if currency and currency.upper() != self._expected_currency.upper():
            findings.append(
                ValidationFinding(
                    code="wrong_currency",
                    message=f"Unexpected currency '{currency}' (expected {self._expected_currency})",
                    severity=Severity.ERROR,
                    filename=filename,
                    field="currency",
                )
            )

        order_col = self._source_for_role(column_map, ("order_id",))
        if order_col and order_col in df.columns:
            series = df[order_col].astype(str).str.strip()
            series = series[series.str.lower().isin({"", "nan", "none", "<na>"}) == False]  # noqa: E712
            dup = int(series.duplicated().sum())
            if dup:
                findings.append(
                    ValidationFinding(
                        code="duplicate_order_ids",
                        message=f"{dup} duplicate order ID(s)",
                        severity=Severity.WARNING,
                        filename=filename,
                        field=order_col,
                    )
                )

        invoice_col = self._source_for_role(column_map, ("pos_invoice",))
        if invoice_col and invoice_col in df.columns:
            inv = df[invoice_col].astype(str).str.strip()
            inv = inv[inv.str.lower().isin({"", "nan", "none", "<na>"}) == False]  # noqa: E712
            dup_inv = int(inv.duplicated().sum())
            if dup_inv:
                findings.append(
                    ValidationFinding(
                        code="duplicate_invoice_numbers",
                        message=f"{dup_inv} duplicate invoice number(s)",
                        severity=Severity.WARNING,
                        filename=filename,
                        field=invoice_col,
                    )
                )

        date_col = self._source_for_role(column_map, ("date",))
        if date_col and date_col in df.columns:
            dates = parse_datetime_series(df[date_col])
            future = int((dates.dt.date > self._as_of).sum()) if dates.notna().any() else 0
            if future:
                findings.append(
                    ValidationFinding(
                        code="future_dates",
                        message=f"{future} row(s) with future dates (as of {self._as_of.isoformat()})",
                        severity=Severity.WARNING,
                        filename=filename,
                        field=date_col,
                    )
                )

        amount_col = self._source_for_role(column_map, ("amount", "settled_amount"))
        if amount_col and amount_col in df.columns:
            amounts = pd.to_numeric(
                df[amount_col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )
            negatives = int((amounts < 0).sum())
            if negatives:
                findings.append(
                    ValidationFinding(
                        code="negative_amounts",
                        message=f"{negatives} negative amount(s)",
                        severity=Severity.WARNING,
                        filename=filename,
                        field=amount_col,
                    )
                )

        return findings

    def validate_batch(self, previews: Iterable[FilePreview]) -> list[ValidationFinding]:
        """Cross-file checks (mixed platforms within a role, etc.)."""
        findings: list[ValidationFinding] = []
        pos = [p for p in previews if p.dataset_role == DatasetRole.POS and p.platform != PlatformKind.UNKNOWN]
        settle = [
            p
            for p in previews
            if p.dataset_role == DatasetRole.SETTLEMENT and p.platform != PlatformKind.UNKNOWN
        ]

        pos_platforms = {p.platform for p in pos}
        if len(pos_platforms) > 1:
            findings.append(
                ValidationFinding(
                    code="mixed_platforms",
                    message=f"Mixed POS platforms in one upload: {', '.join(p.value for p in pos_platforms)}",
                    severity=Severity.ERROR,
                )
            )

        # Settlement may mix Swiggy+Zomato — INFO only
        settle_platforms = {p.platform for p in settle}
        if len(settle_platforms) > 1:
            findings.append(
                ValidationFinding(
                    code="mixed_settlement_platforms",
                    message=(
                        "Multiple settlement platforms detected: "
                        + ", ".join(sorted(p.value for p in settle_platforms))
                    ),
                    severity=Severity.INFO,
                )
            )

        return findings

    @staticmethod
    def _source_for_role(column_map: dict[str, str], roles: tuple[str, ...]) -> str | None:
        for src, role in column_map.items():
            if role in roles:
                return src
        return None
