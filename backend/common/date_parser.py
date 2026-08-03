"""
Enterprise date parser — single source of truth for OmniReconcile ingest.

Never use bare ``pd.to_datetime(value)`` for business date cells.
Prefer explicit formats: ISO first, then Indian DD/MM and DD-MM.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from typing import Any, Iterable

import pandas as pd

# Excel 1900-date system epoch (pandas / Excel serial origin).
_EXCEL_EPOCH = datetime(1899, 12, 30)

# Reasonable Excel serial window (~1900-01-01 … ~2100-01-01).
_EXCEL_SERIAL_MIN = 1.0
_EXCEL_SERIAL_MAX = 73050.0

_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_BLANK = frozenset({"", "nan", "none", "nat", "#ref!", "#n/a", "null", "<na>", "na"})

# Explicit formats — never rely on locale-dependent guessing for slash/dash.
_ISO_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
)

_INDIAN_SLASH_FORMATS: tuple[str, ...] = (
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S.%f",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)

_INDIAN_DASH_FORMATS: tuple[str, ...] = (
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S.%f",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
)

# Rare export variants (still explicit — never month-first slash).
_EXTRA_FORMATS: tuple[str, ...] = (
    "%d %b %Y %H:%M:%S",
    "%d %b %Y",
    "%d %B %Y %H:%M:%S",
    "%d %B %Y",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
)


def parse_datetime(value: Any) -> datetime | None:
    """
    Parse a single cell into a naive ``datetime``.

    Returns ``None`` for blank / NaN / invalid values.
    Indian DD/MM is preferred for slash and non-ISO dash strings.
    """
    if value is None:
        return None

    # Pandas / NumPy missing
    try:
        if value is pd.NaT:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        if pd.isna(value) and not isinstance(value, (datetime, date, pd.Timestamp)):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime().replace(tzinfo=None)

    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    # Excel serial (int/float in date columns)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _from_excel_serial(float(value))

    text = str(value).strip()
    if not text or text.lower() in _BLANK:
        return None

    # Numeric string that looks like Excel serial
    if re.fullmatch(r"\d+(\.\d+)?", text):
        try:
            serial = float(text)
        except ValueError:
            serial = None
        if serial is not None and _EXCEL_SERIAL_MIN <= serial <= _EXCEL_SERIAL_MAX:
            # Prefer serial only when magnitude looks like Excel days, not a year alone.
            if serial >= 200:  # years like 2026 stay out of serial path
                parsed_serial = _from_excel_serial(serial)
                if parsed_serial is not None:
                    return parsed_serial

    # ISO YYYY-MM-DD… (unambiguous)
    if _ISO_DATE.match(text):
        # Normalize trailing Z / offset lightly
        candidate = text.replace("Z", "")
        if "+" in candidate[10:] or candidate.count("-") > 2:
            # Strip timezone offset for naive storage: take datetime part before offset
            for sep in ("+", "-"):
                # only look after the date portion
                idx = candidate.find(sep, 10)
                if idx > 10:
                    candidate = candidate[:idx]
                    break
        parsed = _try_formats(candidate, _ISO_FORMATS)
        if parsed is not None:
            return parsed

    # Indian slash DD/MM/YYYY
    if "/" in text:
        parsed = _try_formats(text, _INDIAN_SLASH_FORMATS)
        if parsed is not None:
            return parsed

    # Dash: if not ISO year-first, treat as Indian DD-MM-YYYY
    if "-" in text and not _ISO_DATE.match(text):
        parsed = _try_formats(text, _INDIAN_DASH_FORMATS)
        if parsed is not None:
            return parsed

    # Named-month and year-first slash extras
    parsed = _try_formats(text, _EXTRA_FORMATS)
    if parsed is not None:
        return parsed

    return None


def parse_datetime_series(values: Any) -> pd.Series:
    """
    Parse a column / iterable into ``datetime64[ns]`` (NaT on failure).

    Use this for DataFrame date columns instead of ``pd.to_datetime``.
    """
    if isinstance(values, pd.Series):
        index = values.index
        parsed = [parse_datetime(v) for v in values.tolist()]
        return pd.Series(parsed, index=index, dtype="datetime64[ns]")

    if isinstance(values, pd.Index):
        parsed = [parse_datetime(v) for v in values.tolist()]
        return pd.Series(parsed, dtype="datetime64[ns]")

    if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        parsed = [parse_datetime(v) for v in values]
        return pd.Series(parsed, dtype="datetime64[ns]")

    single = parse_datetime(values)
    return pd.Series([single], dtype="datetime64[ns]")


def date_range_iso(values: Any) -> tuple[str | None, str | None]:
    """Return (min, max) as ``YYYY-MM-DD`` from a column of mixed date cells."""
    series = parse_datetime_series(values).dropna()
    if series.empty:
        return None, None
    start = series.min()
    end = series.max()
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _from_excel_serial(serial: float) -> datetime | None:
    if math.isnan(serial) or math.isinf(serial):
        return None
    if serial < _EXCEL_SERIAL_MIN or serial > _EXCEL_SERIAL_MAX:
        return None
    try:
        # Preserve fractional day as time component.
        return _EXCEL_EPOCH + timedelta(days=float(serial))
    except (OverflowError, ValueError, OSError):
        return None


def _try_formats(text: str, formats: tuple[str, ...]) -> datetime | None:
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
