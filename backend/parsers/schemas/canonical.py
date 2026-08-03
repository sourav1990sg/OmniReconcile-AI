"""Shared canonical POS field names (parser-agnostic)."""

from __future__ import annotations

from typing import Final

CANONICAL_ORDER_ID: Final[str] = "Aggregator_Order_ID"
CANONICAL_AMOUNT: Final[str] = "Expected_Amount"
CANONICAL_DATE: Final[str] = "Date"
CANONICAL_OUTLET: Final[str] = "Outlet"
CANONICAL_PLATFORM: Final[str] = "Platform"
CANONICAL_STATUS: Final[str] = "Status"
CANONICAL_POS_INVOICE: Final[str] = "POS_Invoice_No"
CANONICAL_SOURCE_FILE: Final[str] = "Source_File"

CANONICAL_COLUMNS: Final[tuple[str, ...]] = (
    CANONICAL_ORDER_ID,
    CANONICAL_AMOUNT,
    CANONICAL_DATE,
    CANONICAL_OUTLET,
    CANONICAL_PLATFORM,
    CANONICAL_STATUS,
    CANONICAL_POS_INVOICE,
    CANONICAL_SOURCE_FILE,
)

ROLE_TO_CANONICAL: Final[dict[str, str]] = {
    "order_id": CANONICAL_ORDER_ID,
    "amount": CANONICAL_AMOUNT,
    "date": CANONICAL_DATE,
    "outlet": CANONICAL_OUTLET,
    "platform": CANONICAL_PLATFORM,
    "status": CANONICAL_STATUS,
    "pos_invoice": CANONICAL_POS_INVOICE,
}
