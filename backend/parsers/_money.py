"""Money and date helpers for settlement parsers (Decimal-first)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal | None:
    """Convert a cell value to Decimal; return None when missing/invalid."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        # Avoid binary float artifacts by going through str for floats
        if isinstance(value, float):
            if value != value:  # NaN
                return None
            return Decimal(str(value))
        return Decimal(value)
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none", "nat", "#ref!", "#n/a"}:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def clean_order_id(value: Any) -> str | None:
    """Normalize an aggregator order id to a clean string."""
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith(".0") and text.replace(".", "", 1).isdigit():
        text = text[:-2]
    if not text or text.lower() in {"nan", "none", "nat", "#ref!", "<na>"}:
        return None
    if "#ref!" in text.lower():
        return None
    return text


def parse_date(value: Any) -> datetime | None:
    """Enterprise date parse (DD/MM-safe). Delegates to ``backend.common.date_parser``."""
    from backend.common.date_parser import parse_datetime

    return parse_datetime(value)
