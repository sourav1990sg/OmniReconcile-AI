"""
Canonical settlement domain models.

Pandas must never leave settlement parsers; business code consumes these types only.
Monetary fields use :class:`decimal.Decimal`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator
from uuid import uuid4


@dataclass(frozen=True)
class CanonicalOrder:
    """One canonical settlement order (platform-agnostic)."""

    aggregator_order_id: str
    settled_amount: Decimal
    settlement_date: datetime | date | None
    platform: str
    source_file: str | None = None
    outlet: str | None = None
    order_status: str | None = None


@dataclass(frozen=True)
class CanonicalDataset:
    """Immutable collection of canonical settlement orders."""

    platform: str
    source: str
    currency: str
    orders: tuple[CanonicalOrder, ...] = ()

    def __len__(self) -> int:
        return len(self.orders)

    def __iter__(self) -> Iterator[CanonicalOrder]:
        return iter(self.orders)

    def all_orders(self) -> tuple[CanonicalOrder, ...]:
        return self.orders

    @classmethod
    def empty(
        cls,
        *,
        platform: str = "",
        source: str = "",
        currency: str = "INR",
    ) -> CanonicalDataset:
        return cls(platform=platform, source=source, currency=currency, orders=())

    def merge(self, other: CanonicalDataset) -> CanonicalDataset:
        """Return a new dataset containing orders from ``self`` and ``other``."""
        platforms = {p for p in (self.platform, other.platform) if p and p != "mixed"}
        if self.platform == "mixed":
            platforms.update(
                o.platform for o in self.orders if o.platform
            )
        if other.platform == "mixed":
            platforms.update(
                o.platform for o in other.orders if o.platform
            )
        # Also infer from order platforms when merging non-empty sides
        platforms.update(o.platform for o in self.orders if o.platform)
        platforms.update(o.platform for o in other.orders if o.platform)

        platform = next(iter(platforms)) if len(platforms) == 1 else ("mixed" if platforms else "")
        source_labels = {
            {"swiggy": "Swiggy Settlement", "zomato": "Zomato Settlement"}.get(p, p)
            for p in platforms
        }
        source = " + ".join(sorted(source_labels)) if source_labels else (self.source or other.source)
        currency = self.currency or other.currency or "INR"
        return CanonicalDataset(
            platform=platform,
            source=source,
            currency=currency,
            orders=self.orders + other.orders,
        )


@dataclass
class DatasetMetadata:
    """Structured metadata for an ingested settlement dataset."""

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
    negative_amounts: int = 0
    platforms: list[str] = field(default_factory=list)

    @staticmethod
    def new_ids() -> tuple[str, str]:
        return str(uuid4()), str(uuid4())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    """Validation finding for settlement ingestion."""

    code: str
    message: str
    filename: str | None = None
    severity: str = "error"


@dataclass
class SettlementIngestionResult:
    """Sprint-2 settlement ingestion output."""

    metadata: DatasetMetadata
    dataset: CanonicalDataset
    issues: list[ValidationIssue] = field(default_factory=list)
    files_processed: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        payload = self.metadata.to_dict()
        payload["issues"] = [asdict(i) for i in self.issues]
        payload["files_processed"] = list(self.files_processed)
        payload["order_count"] = len(self.dataset)
        return payload
