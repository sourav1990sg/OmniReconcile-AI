"""Zomato settlement report schema (aliases + hints)."""

from __future__ import annotations

from typing import Final

PLATFORM: Final[str] = "zomato"
SOURCE: Final[str] = "Zomato Settlement"
DEFAULT_CURRENCY: Final[str] = "INR"
ORDER_LEVEL_SHEET: Final[str] = "Order Level"

REQUIRED_ROLES: Final[tuple[str, ...]] = (
    "order_id",
    "settled_amount",
)

COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "order_id": (
        "order id",
        "order_id",
        "order no",
    ),
    "settled_amount": (
        "order level payout",
        "net payout",
        "settled amount",
        "payout",
    ),
    "date": (
        "order date",
        "settlement date",
        "date",
    ),
    "status": (
        "settlement status",
        "status",
    ),
    "outlet": (
        "res. name",
        "res name",
        "restaurant name",
        "outlet",
    ),
}

PREFERRED_EXACT: Final[dict[str, tuple[str, ...]]] = {
    "order_id": ("order id",),
    "date": ("order date",),
    "settled_amount": ("order level payout",),
    "outlet": ("res. name", "res name"),
}

FILENAME_HINTS: Final[tuple[str, ...]] = (
    "zomato",
)

# Prefer Order Date over Settlement date when both exist
DATE_PREFERRED: Final[tuple[str, ...]] = ("order date",)
