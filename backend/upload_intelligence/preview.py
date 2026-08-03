"""Build per-file upload previews from detection + light frame scans."""

from __future__ import annotations

import hashlib
from datetime import date

import pandas as pd

from backend.common.date_parser import date_range_iso
from backend.parsers.schemas import petpooja_schema
from backend.parsers.swiggy import schema as swiggy_schema
from backend.parsers.zomato import schema as zomato_schema
from backend.upload_intelligence.detector import ColumnFileDetector, FileDetectionResult
from backend.upload_intelligence.models import (
    FilePreview,
    PlatformKind,
    PreviewStatus,
    Severity,
    ValidationFinding,
)
from backend.upload_intelligence.validator import UploadValidator


class PreviewBuilder:
    """Assemble FilePreview cards (READY / WARNING / FAILED)."""

    def __init__(
        self,
        detector: ColumnFileDetector | None = None,
        validator: UploadValidator | None = None,
        *,
        reference_date: date | None = None,
    ) -> None:
        self._detector = detector or ColumnFileDetector()
        self._validator = validator or UploadValidator(reference_date=reference_date)

    def build(self, filename: str, content: bytes) -> FilePreview:
        detection = self._detector.detect(filename, content)
        return self.from_detection(detection, content)

    def from_detection(self, detection: FileDetectionResult, content: bytes) -> FilePreview:
        winner = detection.winner
        df = detection.frame.dataframe
        checksum = hashlib.sha256(content).hexdigest()[:16]

        findings = list(detection.findings)
        findings.extend(
            self._validator.validate_frame(
                filename=detection.filename,
                platform=winner.platform,
                column_map=winner.column_map,
                df=df,
                currency=winner.currency,
                load_error=detection.frame.load_error
                if detection.frame.load_error and df.empty
                else None,
            )
        )

        rows = int(len(df)) if df is not None else 0
        cancelled = 0
        eligible = rows
        duplicates = 0
        date_from = date_to = None
        outlets: list[str] = []

        if winner.matched and rows and not df.empty:
            cancelled, eligible = self._cancelled_eligible(winner.platform, winner.column_map, df)
            duplicates = self._duplicate_orders(winner.column_map, df)
            date_from, date_to = self._date_range(winner.column_map, df)
            outlets = self._outlets(winner.column_map, df)

        status = self._status(findings, winner.matched)
        warnings = [
            f.message
            for f in findings
            if f.severity in (Severity.WARNING, Severity.INFO)
        ]
        # Always surface unknown / low-confidence reasons
        reasons = list(winner.reasons)

        return FilePreview(
            filename=detection.filename,
            platform=winner.platform,
            confidence_pct=winner.confidence_pct,
            status=status,
            dataset_role=winner.dataset_role,
            rows=rows,
            cancelled_orders=cancelled,
            eligible_orders=eligible,
            duplicate_orders=duplicates,
            date_from=date_from,
            date_to=date_to,
            outlets=outlets,
            warnings=warnings,
            findings=findings,
            reasons=reasons,
            column_map=dict(winner.column_map),
            checksum=checksum,
            currency=winner.currency,
            source=winner.source,
            candidates=list(detection.candidates),
        )

    def _status(self, findings: list[ValidationFinding], matched: bool) -> PreviewStatus:
        if not matched or any(f.severity == Severity.ERROR for f in findings):
            return PreviewStatus.FAILED
        if any(f.severity == Severity.WARNING for f in findings):
            return PreviewStatus.WARNING
        return PreviewStatus.READY

    def _cancelled_eligible(
        self,
        platform: PlatformKind,
        column_map: dict[str, str],
        df: pd.DataFrame,
    ) -> tuple[int, int]:
        status_col = next((src for src, role in column_map.items() if role == "status"), None)
        tokens: tuple[str, ...] = ()
        if platform == PlatformKind.PETPOOJA:
            tokens = petpooja_schema.CANCELLED_STATUS_TOKENS
        elif platform == PlatformKind.SWIGGY:
            tokens = swiggy_schema.CANCELLED_STATUS_TOKENS
        elif platform == PlatformKind.ZOMATO:
            tokens = ()  # Zomato schema has no cancelled tokens list; treat none
        if not status_col or status_col not in df.columns or not tokens:
            return 0, int(len(df))
        status = df[status_col].astype(str).str.strip().str.lower().fillna("")
        mask = status.map(lambda s: any(t in str(s) for t in tokens if t))
        cancelled = int(mask.sum())
        return cancelled, int(len(df)) - cancelled

    @staticmethod
    def _duplicate_orders(column_map: dict[str, str], df: pd.DataFrame) -> int:
        order_col = next((src for src, role in column_map.items() if role == "order_id"), None)
        if not order_col or order_col not in df.columns:
            return 0
        series = df[order_col].astype(str).str.strip()
        series = series[~series.str.lower().isin({"", "nan", "none", "<na>"})]
        return int(series.duplicated().sum())

    @staticmethod
    def _date_range(column_map: dict[str, str], df: pd.DataFrame) -> tuple[str | None, str | None]:
        date_col = next((src for src, role in column_map.items() if role == "date"), None)
        if not date_col or date_col not in df.columns:
            return None, None
        return date_range_iso(df[date_col])

    @staticmethod
    def _outlets(column_map: dict[str, str], df: pd.DataFrame) -> list[str]:
        outlet_col = next((src for src, role in column_map.items() if role == "outlet"), None)
        if not outlet_col or outlet_col not in df.columns:
            return []
        values = {
            str(v).strip()
            for v in df[outlet_col].dropna().unique()
            if str(v).strip() and str(v).strip().lower() not in {"nan", "none", "<na>"}
        }
        return sorted(values)
