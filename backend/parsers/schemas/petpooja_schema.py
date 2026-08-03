"""
Petpooja POS report schema: column aliases and detection hints.

All Petpooja-specific header mappings live here so the ingestion package
remains parser-agnostic.
"""

from __future__ import annotations

from typing import Final

PLATFORM: Final[str] = "petpooja"
SOURCE: Final[str] = "Petpooja POS"
DEFAULT_CURRENCY: Final[str] = "INR"

REQUIRED_ROLES: Final[tuple[str, ...]] = (
    "order_id",
    "amount",
    "date",
    "outlet",
)

COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "order_id": (
        "aggregator order no",
        "aggregator order no.",
        "aggregator_order_no",
        "aggregator order id",
    ),
    "amount": (
        "my amount",
        "my_amount",
        "expected amount",
        "expected_amount",
    ),
    "date": (
        "date",
        "order date",
        "invoice date",
    ),
    "outlet": (
        "outlet name",
        "outlet_name",
        "restaurant name",
        "restaurant",
    ),
    "platform": (
        "order from",
        "order_from",
        "platform",
        "aggregator",
    ),
    "status": (
        "status",
        "order status",
        "delivery status",
    ),
    "pos_invoice": (
        "pos invoice no",
        "pos invoice no.",
        "pos_invoice_no",
        "invoice no",
        "invoice_no",
    ),
}

PREFERRED_EXACT: Final[dict[str, tuple[str, ...]]] = {
    "date": ("date",),
    "status": ("status",),
    "outlet": ("outlet name", "outlet_name"),
}

CANCELLED_STATUS_TOKENS: Final[tuple[str, ...]] = (
    "cancel",
    "cancelled",
    "canceled",
    "void",
)

FILENAME_HINTS: Final[tuple[str, ...]] = (
    "order_report",
    "petpooja",
    "pos",
    "order_summary",
)
