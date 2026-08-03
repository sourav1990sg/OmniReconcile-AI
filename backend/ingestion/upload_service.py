"""
Upload orchestration for POS report ingestion.

Responsibilities (parser-agnostic):
- file loading
- file detection
- validation
- routing to the appropriate parser
- assembling DatasetMetadata + CanonicalDataset
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Sequence

import pandas as pd

from backend.common.date_parser import date_range_iso
from backend.ingestion.detector import DetectionResult, FileDetector, PetpoojaReportDetector
from backend.ingestion.loader import FileLoader
from backend.ingestion.logging_utils import log_with_context
from backend.ingestion.merger import DatasetMerger, PosReportMerger
from backend.ingestion.models import (
    CanonicalDataset,
    DatasetMetadata,
    FileIngestRecord,
    IngestionResult,
    ValidationIssue,
)
from backend.ingestion.router import ParserRouter
from backend.ingestion.validator import DatasetValidator, PetpoojaReportValidator, QualityMetrics
from backend.parsers.petpooja import PetpoojaParser
from backend.parsers.registry import ParserRegistry
from backend.parsers.schemas.canonical import CANONICAL_DATE, CANONICAL_OUTLET

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadedFile:
    """In-memory upload payload (filename + bytes)."""

    filename: str
    content: bytes


class PosUploadService:
    """
    Data Ingestion Engine entry point.

    Loads → detects → validates → routes to parser → merges → metadata.
    """

    def __init__(
        self,
        detector: FileDetector | PetpoojaReportDetector | None = None,
        validator: DatasetValidator | PetpoojaReportValidator | None = None,
        merger: DatasetMerger | PosReportMerger | None = None,
        *,
        registry: ParserRegistry | None = None,
        loader: FileLoader | None = None,
        router: ParserRouter | None = None,
        skip_invalid_files: bool = True,
        session_id: str | None = None,
        upload_id: str | None = None,
        default_currency: str = "INR",
    ) -> None:
        self._registry = registry or ParserRegistry()
        self._loader = loader or FileLoader()
        self._detector = detector or FileDetector(self._registry)
        self._validator = validator or DatasetValidator()
        self._merger = merger or DatasetMerger()
        self._router = router or ParserRouter(self._registry)
        self._skip_invalid_files = skip_invalid_files
        self._session_id = session_id
        self._upload_id = upload_id
        self._default_currency = default_currency
        self._petpooja = PetpoojaParser()

    def ingest(self, files: Sequence[UploadedFile | tuple[str, bytes]]) -> IngestionResult:
        """Ingest one or many POS reports into metadata + canonical dataset."""
        uploaded = [self._coerce_upload(f) for f in files]
        session_id, upload_id = self._resolve_ids()

        if not uploaded:
            log_with_context(
                logger,
                logging.ERROR,
                "Ingest called with zero files",
                session_id=session_id,
                upload_id=upload_id,
            )
            metadata = self._empty_metadata(session_id, upload_id, total_files=0)
            return IngestionResult(
                metadata=metadata,
                dataset=CanonicalDataset.empty(currency=self._default_currency),
                issues=[
                    ValidationIssue(
                        code="no_files",
                        message="No files were provided for ingestion",
                    )
                ],
            )

        normalized_frames: list[pd.DataFrame] = []
        file_records: list[FileIngestRecord] = []
        all_issues: list[ValidationIssue] = []
        parse_null_order_ids = 0
        parse_null_amounts = 0
        platform = ""
        source = ""
        currency = self._default_currency

        for item in uploaded:
            record, frame, issues, stats = self._process_one(item, session_id, upload_id)
            file_records.append(record)
            all_issues.extend(issues)
            parse_null_order_ids += stats.get("null_order_ids", 0)
            parse_null_amounts += stats.get("null_amounts", 0)
            if frame is not None and not frame.empty:
                normalized_frames.append(frame)
                platform = stats.get("platform") or platform
                source = stats.get("source") or source
                currency = stats.get("currency") or currency

        merged = self._merger.merge(normalized_frames)
        validation, quality = self._validator.validate_dataset(
            merged,
            null_order_ids_from_parse=parse_null_order_ids,
            null_amounts_from_parse=parse_null_amounts,
        )
        all_issues.extend(validation.issues)

        return self._build_result(
            session_id=session_id,
            upload_id=upload_id,
            total_files=len(uploaded),
            merged=merged,
            files=file_records,
            issues=all_issues,
            quality=quality,
            platform=platform or "unknown",
            source=source or "unknown",
            currency=currency,
        )

    def ingest_paths(self, paths: Sequence[str | Path]) -> IngestionResult:
        """Convenience helper: ingest reports from filesystem paths."""
        uploads = [UploadedFile(filename=Path(p).name, content=Path(p).read_bytes()) for p in paths]
        return self.ingest(uploads)

    def read_dataframe(self, filename: str, content: bytes) -> pd.DataFrame:
        """Load a spreadsheet; optionally rediscover header by column names."""
        df = self._loader.load(filename, content)
        detection = self._detector.detect_from_dataframe(df, filename)
        if not detection.matched:
            discovered = self._loader.discover_header_frame(
                content,
                filename,
                is_match=lambda probe, name: self._detector.detect_from_dataframe(
                    probe, name
                ).matched,
            )
            if discovered is not None:
                return discovered
        return df

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_one(
        self,
        item: UploadedFile,
        session_id: str,
        upload_id: str,
    ) -> tuple[FileIngestRecord, pd.DataFrame | None, list[ValidationIssue], dict]:
        issues: list[ValidationIssue] = []
        filename = item.filename or "unknown"
        stats: dict = {}

        if not self._detector.is_supported_filename(filename):
            issue = ValidationIssue(
                code="unsupported_extension",
                message=f"Unsupported file extension for '{filename}'",
                filename=filename,
            )
            issues.append(issue)
            return (
                FileIngestRecord(filename=filename, rows_read=0, is_petpooja=False, issues=issues),
                None,
                issues,
                stats,
            )

        try:
            raw = self.read_dataframe(filename, item.content)
        except Exception as exc:  # noqa: BLE001
            log_with_context(
                logger,
                logging.ERROR,
                "Failed to read file",
                filename=filename,
                session_id=session_id,
                upload_id=upload_id,
                error=str(exc),
            )
            issue = ValidationIssue(
                code="unreadable_file",
                message=f"Could not read file: {exc}",
                filename=filename,
            )
            issues.append(issue)
            return (
                FileIngestRecord(filename=filename, rows_read=0, is_petpooja=False, issues=issues),
                None,
                issues,
                stats,
            )

        detection = self._detector.detect_from_dataframe(raw, filename)
        validation = self._validator.validate_file(raw, filename=filename, detection=detection)
        issues.extend(validation.issues)

        record = FileIngestRecord(
            filename=filename,
            rows_read=len(raw),
            is_petpooja=detection.is_petpooja,
            platform=detection.platform,
            parser_id=detection.parser_id,
            issues=list(validation.issues),
        )

        if not validation.is_valid:
            if self._skip_invalid_files:
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Skipping invalid file",
                    filename=filename,
                    session_id=session_id,
                    upload_id=upload_id,
                    platform=detection.platform,
                )
                return record, None, issues, stats
            raise ValueError(f"Invalid file '{filename}': {[i.message for i in issues]}")

        parsed = self._router.parse(raw, detection, source_file=filename)
        stats = {
            "null_order_ids": parsed.null_order_ids,
            "null_amounts": parsed.null_amounts,
            "platform": parsed.platform,
            "source": parsed.source,
            "currency": parsed.currency,
        }
        return record, parsed.dataframe, issues, stats

    def _build_result(
        self,
        *,
        session_id: str,
        upload_id: str,
        total_files: int,
        merged: pd.DataFrame,
        files: list[FileIngestRecord],
        issues: list[ValidationIssue],
        quality: QualityMetrics,
        platform: str,
        source: str,
        currency: str,
    ) -> IngestionResult:
        cancelled_mask = self._petpooja.cancelled_mask(merged)
        cancelled = int(cancelled_mask.sum()) if len(merged) else 0
        total_orders = int(len(merged))
        eligible = total_orders - cancelled
        dup_agg = quality.duplicate_aggregator_orders or self._merger.duplicate_order_count(merged)

        start_date: str | None = None
        end_date: str | None = None
        if len(merged) and CANONICAL_DATE in merged.columns:
            start_date, end_date = date_range_iso(merged[CANONICAL_DATE])

        outlets: list[str] = []
        if len(merged) and CANONICAL_OUTLET in merged.columns:
            outlets = sorted(
                {
                    str(o).strip()
                    for o in merged[CANONICAL_OUTLET].dropna().unique()
                    if str(o).strip() and str(o).strip().lower() not in {"nan", "none", "<na>"}
                }
            )

        metadata = DatasetMetadata(
            session_id=session_id,
            upload_id=upload_id,
            platform=platform,
            source=source,
            total_files=total_files,
            total_orders=total_orders,
            cancelled_orders=cancelled,
            eligible_orders=eligible,
            duplicate_orders=dup_agg,
            duplicate_invoice_numbers=quality.duplicate_invoice_numbers,
            duplicate_aggregator_orders=dup_agg,
            null_order_ids=quality.null_order_ids,
            null_amounts=quality.null_amounts,
            future_dates=quality.future_dates,
            outlets=outlets,
            start_date=start_date,
            end_date=end_date,
            currency=currency,
        )
        dataset = CanonicalDataset(
            platform=platform,
            source=source,
            currency=currency,
            _frame=merged,
        )

        log_with_context(
            logger,
            logging.INFO,
            "Ingestion complete",
            session_id=session_id,
            upload_id=upload_id,
            platform=platform,
            total_files=total_files,
            total_orders=total_orders,
            cancelled_orders=cancelled,
            eligible_orders=eligible,
            duplicate_orders=dup_agg,
            start_date=start_date,
            end_date=end_date,
        )
        return IngestionResult(
            metadata=metadata,
            dataset=dataset,
            files=files,
            issues=issues,
        )

    def _resolve_ids(self) -> tuple[str, str]:
        session_id, upload_id = DatasetMetadata.new_ids()
        return self._session_id or session_id, self._upload_id or upload_id

    def _empty_metadata(self, session_id: str, upload_id: str, *, total_files: int) -> DatasetMetadata:
        return DatasetMetadata(
            session_id=session_id,
            upload_id=upload_id,
            platform="",
            source="",
            total_files=total_files,
            total_orders=0,
            cancelled_orders=0,
            eligible_orders=0,
            duplicate_orders=0,
            duplicate_invoice_numbers=0,
            duplicate_aggregator_orders=0,
            null_order_ids=0,
            null_amounts=0,
            future_dates=0,
            outlets=[],
            start_date=None,
            end_date=None,
            currency=self._default_currency,
        )

    @staticmethod
    def _coerce_upload(item: UploadedFile | tuple[str, bytes] | BinaryIO) -> UploadedFile:
        if isinstance(item, UploadedFile):
            return item
        if isinstance(item, tuple) and len(item) == 2:
            name, data = item
            return UploadedFile(filename=str(name), content=data)
        raise TypeError(f"Unsupported upload type: {type(item)!r}")
