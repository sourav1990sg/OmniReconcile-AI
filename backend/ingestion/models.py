"""Domain models for the parser-agnostic ingestion engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterator, Sequence
from uuid import uuid4

import pandas as pd

from backend.common.date_parser import parse_datetime
from backend.parsers.schemas.canonical import CANONICAL_COLUMNS


@dataclass(frozen=True)
class DateRange:
    """Inclusive calendar span covered by the ingested orders."""

    from_date: str | None
    to_date: str | None

    def to_dict(self) -> dict[str, str | None]:
        """Serialize using the API keys ``from`` / ``to``."""
        return {"from": self.from_date, "to": self.to_date}


@dataclass
class ValidationIssue:
    """A single validation finding for an uploaded file or dataset."""

    code: str
    message: str
    filename: str | None = None
    severity: str = "error"


@dataclass
class FileIngestRecord:
    """Per-file parse metadata retained for logging and diagnostics."""

    filename: str
    rows_read: int
    is_petpooja: bool
    platform: str | None = None
    parser_id: str | None = None
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass(frozen=True)
class CanonicalOrder:
    """One canonical POS order exposed to business modules (no Pandas)."""

    aggregator_order_id: str
    expected_amount: float
    date: datetime | None
    outlet: str | None
    platform: str | None
    status: str | None
    pos_invoice_no: str | None
    source_file: str | None


@dataclass
class CanonicalDataset:
    """
    Parser-agnostic canonical POS dataset.

    Internal storage may use Pandas; business modules should consume
    :meth:`orders` / iteration — not the private frame.
    """

    platform: str
    source: str
    currency: str
    _frame: pd.DataFrame = field(repr=False)

    def __len__(self) -> int:
        return int(len(self._frame))

    def __iter__(self) -> Iterator[CanonicalOrder]:
        return iter(self.orders())

    def orders(self) -> tuple[CanonicalOrder, ...]:
        """Return immutable canonical order records."""
        if self._frame is None or self._frame.empty:
            return ()
        records: list[CanonicalOrder] = []
        for row in self._frame.itertuples(index=False):
            date_val = getattr(row, "Date", None)
            if pd.isna(date_val):
                date_parsed: datetime | None = None
            elif isinstance(date_val, datetime):
                date_parsed = date_val
            else:
                date_parsed = parse_datetime(date_val)

            def _str(val: object) -> str | None:
                if val is None or (isinstance(val, float) and pd.isna(val)):
                    return None
                text = str(val).strip()
                return None if text.lower() in {"", "nan", "none", "<na>", "nat"} else text

            amount = getattr(row, "Expected_Amount", 0.0)
            try:
                amount_f = float(amount) if not pd.isna(amount) else 0.0
            except (TypeError, ValueError):
                amount_f = 0.0

            records.append(
                CanonicalOrder(
                    aggregator_order_id=str(getattr(row, "Aggregator_Order_ID", "")),
                    expected_amount=amount_f,
                    date=date_parsed,
                    outlet=_str(getattr(row, "Outlet", None)),
                    platform=_str(getattr(row, "Platform", None)),
                    status=_str(getattr(row, "Status", None)),
                    pos_invoice_no=_str(getattr(row, "POS_Invoice_No", None)),
                    source_file=_str(getattr(row, "Source_File", None)),
                )
            )
        return tuple(records)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Escape hatch for infrastructure code.

        Business modules must not depend on this; prefer :meth:`orders`.
        """
        if self._frame is None:
            return pd.DataFrame(columns=list(CANONICAL_COLUMNS))
        return self._frame.copy()

    @classmethod
    def empty(cls, *, platform: str = "", source: str = "", currency: str = "INR") -> CanonicalDataset:
        return cls(
            platform=platform,
            source=source,
            currency=currency,
            _frame=pd.DataFrame(columns=list(CANONICAL_COLUMNS)),
        )


@dataclass
class DatasetMetadata:
    """Structured metadata describing an ingested canonical dataset."""

    session_id: str
    upload_id: str
    platform: str
    source: str
    total_files: int
    total_orders: int
    cancelled_orders: int
    eligible_orders: int
    duplicate_orders: int
    duplicate_invoice_numbers: int
    duplicate_aggregator_orders: int
    null_order_ids: int
    null_amounts: int
    future_dates: int
    outlets: list[str]
    start_date: str | None
    end_date: str | None
    currency: str

    @staticmethod
    def new_ids() -> tuple[str, str]:
        """Allocate a fresh ``(session_id, upload_id)`` pair."""
        return str(uuid4()), str(uuid4())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionResult:
    """
    Ingestion pipeline output: metadata + canonical dataset.

    Sprint-1 attribute accessors (``total_files``, ``merged_dataframe``, …)
    remain available for backward compatibility.
    """

    metadata: DatasetMetadata
    dataset: CanonicalDataset
    files: list[FileIngestRecord] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Sprint-1 compatibility surface
    # ------------------------------------------------------------------

    @property
    def total_files(self) -> int:
        return self.metadata.total_files

    @property
    def total_orders(self) -> int:
        return self.metadata.total_orders

    @property
    def cancelled_orders(self) -> int:
        return self.metadata.cancelled_orders

    @property
    def eligible_orders(self) -> int:
        return self.metadata.eligible_orders

    @property
    def duplicate_orders(self) -> int:
        return self.metadata.duplicate_orders

    @property
    def outlets(self) -> list[str]:
        return list(self.metadata.outlets)

    @property
    def date_range(self) -> DateRange:
        return DateRange(self.metadata.start_date, self.metadata.end_date)

    @property
    def merged_dataframe(self) -> pd.DataFrame:
        """Deprecated: use :attr:`dataset` / :meth:`CanonicalDataset.orders`."""
        return self.dataset.to_dataframe()

    def to_dict(self) -> dict[str, Any]:
        """Sprint-1 response payload (includes ``merged_dataframe`` for BC)."""
        return {
            "total_files": self.total_files,
            "total_orders": self.total_orders,
            "cancelled_orders": self.cancelled_orders,
            "eligible_orders": self.eligible_orders,
            "duplicate_orders": self.duplicate_orders,
            "date_range": self.date_range.to_dict(),
            "outlets": list(self.outlets),
            "merged_dataframe": self.merged_dataframe,
            "metadata": self.metadata.to_dict(),
            "dataset": self.dataset,
        }

    def summary_without_dataframe(self) -> dict[str, Any]:
        """JSON-friendly summary excluding DataFrame / dataset payload."""
        payload = self.to_dict()
        payload.pop("merged_dataframe", None)
        payload.pop("dataset", None)
        payload["issues"] = [asdict(i) for i in self.issues]
        return payload
