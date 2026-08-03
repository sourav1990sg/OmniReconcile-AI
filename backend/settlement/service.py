"""
Settlement Ingestion Engine (Sprint 2).

Orchestrates Swiggy/Zomato (and future) settlement parsers into
DatasetMetadata + CanonicalDataset. Does not touch POS ingestion or reconciliation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from backend.ingestion.logging_utils import log_with_context
from backend.parsers.canonical import (
    CanonicalDataset,
    CanonicalOrder,
    DatasetMetadata,
    SettlementIngestionResult,
    ValidationIssue,
)
from backend.parsers.settlement_base import SettlementParseResult
from backend.parsers.settlement_registry import SettlementParserRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadedSettlementFile:
    """In-memory settlement upload."""

    filename: str
    content: bytes


class SettlementUploadService:
    """
    Sprint-2 entry point: detect → parse (via registry) → merge → metadata.

    Open/Closed: register Blinkit/Zepto/Magicpin parsers on the registry
    without changing this service.
    """

    def __init__(
        self,
        registry: SettlementParserRegistry | None = None,
        *,
        session_id: str | None = None,
        upload_id: str | None = None,
        reference_date: date | None = None,
        skip_invalid_files: bool = True,
    ) -> None:
        self._registry = registry or SettlementParserRegistry()
        self._session_id = session_id
        self._upload_id = upload_id
        self._reference_date = reference_date
        self._skip_invalid_files = skip_invalid_files

    def ingest(
        self,
        files: Sequence[UploadedSettlementFile | tuple[str, bytes]],
    ) -> SettlementIngestionResult:
        uploaded = [self._coerce(f) for f in files]
        session_id, upload_id = self._ids()

        if not uploaded:
            meta = self._empty_metadata(session_id, upload_id, total_files=0)
            return SettlementIngestionResult(
                metadata=meta,
                dataset=CanonicalDataset.empty(),
                issues=[
                    ValidationIssue(
                        code="no_files",
                        message="No settlement files were provided",
                    )
                ],
            )

        merged = CanonicalDataset.empty()
        all_issues: list[ValidationIssue] = []
        files_processed: list[str] = []
        totals = {
            "null_order_ids": 0,
            "null_amounts": 0,
            "negative_amounts": 0,
            "future_dates": 0,
            "duplicate_order_ids": 0,
            "cancelled": 0,
        }
        platforms: set[str] = set()

        for item in uploaded:
            parser, detection = self._registry.detect(item.filename, item.content)
            if parser is None or detection is None:
                issue = ValidationIssue(
                    code="unrecognized_settlement_file",
                    message=f"No settlement parser matched '{item.filename}'",
                    filename=item.filename,
                )
                all_issues.append(issue)
                if not self._skip_invalid_files:
                    raise ValueError(issue.message)
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Skipping unrecognized settlement file",
                    filename=item.filename,
                    session_id=session_id,
                )
                continue

            result = parser.parse(item.filename, item.content)
            all_issues.extend(result.issues)
            if not result.is_valid:
                if not self._skip_invalid_files:
                    raise ValueError(f"Invalid settlement file '{item.filename}'")
                log_with_context(
                    logger,
                    logging.WARNING,
                    "Skipping invalid settlement file",
                    filename=item.filename,
                    parser_id=parser.parser_id,
                    session_id=session_id,
                )
                continue

            files_processed.append(item.filename)
            platforms.add(parser.platform)
            merged = merged.merge(result.dataset)
            totals["null_order_ids"] += result.null_order_ids
            totals["null_amounts"] += result.null_amounts
            totals["negative_amounts"] += result.negative_amounts
            totals["future_dates"] += result.future_dates
            totals["duplicate_order_ids"] += result.duplicate_order_ids
            totals["cancelled"] += self._count_cancelled(result.dataset)

        # Cross-file duplicate aggregator IDs
        cross_dup = self._cross_file_duplicate_ids(merged.orders)
        if cross_dup:
            all_issues.append(
                ValidationIssue(
                    code="duplicate_order_ids",
                    message=(
                        f"{cross_dup} distinct Aggregator_Order_ID value(s) appear more than once "
                        "across settlement files"
                    ),
                    severity="warning",
                )
            )

        metadata = self._build_metadata(
            session_id=session_id,
            upload_id=upload_id,
            total_files=len(uploaded),
            dataset=merged,
            platforms=sorted(platforms),
            totals=totals,
            cross_file_duplicates=cross_dup,
        )

        log_with_context(
            logger,
            logging.INFO,
            "Settlement ingestion complete",
            session_id=session_id,
            upload_id=upload_id,
            total_files=len(uploaded),
            files_processed=len(files_processed),
            total_orders=metadata.total_orders,
            platforms=metadata.platforms,
        )
        return SettlementIngestionResult(
            metadata=metadata,
            dataset=merged,
            issues=all_issues,
            files_processed=files_processed,
        )

    def ingest_paths(self, paths: Sequence[str | Path]) -> SettlementIngestionResult:
        uploads = [
            UploadedSettlementFile(filename=Path(p).name, content=Path(p).read_bytes())
            for p in paths
        ]
        return self.ingest(uploads)

    # ------------------------------------------------------------------

    def _build_metadata(
        self,
        *,
        session_id: str,
        upload_id: str,
        total_files: int,
        dataset: CanonicalDataset,
        platforms: list[str],
        totals: dict[str, int],
        cross_file_duplicates: int,
    ) -> DatasetMetadata:
        orders = dataset.orders
        total_orders = len(orders)
        cancelled = totals["cancelled"]
        eligible = total_orders  # orders already exclude null id/amount
        dup = cross_file_duplicates

        dates = [
            o.settlement_date
            for o in orders
            if o.settlement_date is not None
        ]
        start = end = None
        if dates:
            norm = [d.date() if isinstance(d, datetime) else d for d in dates]
            start = min(norm).isoformat()
            end = max(norm).isoformat()

        outlets = sorted(
            {
                o.outlet
                for o in orders
                if o.outlet and o.outlet.lower() not in {"nan", "none"}
            }
        )

        platform = platforms[0] if len(platforms) == 1 else ("mixed" if platforms else "")
        source = dataset.source or " + ".join(platforms)

        return DatasetMetadata(
            session_id=session_id,
            upload_id=upload_id,
            platform=platform,
            source=source,
            total_files=total_files,
            total_orders=total_orders,
            cancelled_orders=cancelled,
            eligible_orders=eligible,
            duplicate_orders=dup,
            duplicate_invoice_numbers=0,
            duplicate_aggregator_orders=dup,
            null_order_ids=totals["null_order_ids"],
            null_amounts=totals["null_amounts"],
            future_dates=totals["future_dates"],
            outlets=outlets,
            start_date=start,
            end_date=end,
            currency=dataset.currency or "INR",
            negative_amounts=totals["negative_amounts"],
            platforms=platforms,
        )

    @staticmethod
    def _count_cancelled(dataset: CanonicalDataset) -> int:
        tokens = ("cancel", "cancelled", "canceled", "void")
        count = 0
        for order in dataset.orders:
            status = (order.order_status or "").lower()
            if any(t in status for t in tokens):
                count += 1
        return count

    @staticmethod
    def _cross_file_duplicate_ids(orders: tuple[CanonicalOrder, ...]) -> int:
        counts: dict[str, int] = {}
        for order in orders:
            counts[order.aggregator_order_id] = counts.get(order.aggregator_order_id, 0) + 1
        return sum(1 for c in counts.values() if c > 1)

    def _ids(self) -> tuple[str, str]:
        sid, uid = DatasetMetadata.new_ids()
        return self._session_id or sid, self._upload_id or uid

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
            currency="INR",
            negative_amounts=0,
            platforms=[],
        )

    @staticmethod
    def _coerce(item: UploadedSettlementFile | tuple[str, bytes]) -> UploadedSettlementFile:
        if isinstance(item, UploadedSettlementFile):
            return item
        if isinstance(item, tuple) and len(item) == 2:
            return UploadedSettlementFile(filename=str(item[0]), content=item[1])
        raise TypeError(f"Unsupported upload type: {type(item)!r}")
