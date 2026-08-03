"""Swiggy settlement report schema (aliases + hints)."""

from __future__ import annotations

from typing import Final

PLATFORM: Final[str] = "swiggy"
SOURCE: Final[str] = "Swiggy Settlement"
DEFAULT_CURRENCY: Final[str] = "INR"

REQUIRED_ROLES: Final[tuple[str, ...]] = (
    "order_id",
    "settled_amount",
)

COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "order_id": (
        "order no",
        "order_no",
        "order id",
        "order_id",
    ),
    "settled_amount": (
        "net payable amount (after tcs and tds deduction)",
        "net payable amount (after",
        "net payout",
        "settled amount",
        "settled",
    ),
    "date": (
        "order date",
        "settlement date",
        "date",
    ),
    "status": (
        "order status",
        "status",
    ),
    "outlet": (
        "rid",
        "restaurant id",
        "restaurant name",
        "outlet",
    ),
}

PREFERRED_EXACT: Final[dict[str, tuple[str, ...]]] = {
    "order_id": ("order no", "order_no"),
    "date": ("order date",),
    "status": ("order status",),
}

FILENAME_HINTS: Final[tuple[str, ...]] = (
    "swiggy",
    "annexure",
    "consolidate-annexure",
)

CANCELLED_STATUS_TOKENS: Final[tuple[str, ...]] = (
    "cancel",
    "cancelled",
    "canceled",
    "void",
)
