"""Column-name helpers for financial engines (no positional indexes)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from backend.parsers.column_mapper import normalize_header


def money(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(",", "").replace("₹", "")
    if not text or text.lower() in {"nan", "none", "<na>", "#ref!", "-", "—"}:
        return Decimal("0")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def find_column(columns: Sequence[str], aliases: Sequence[str]) -> str | None:
    """Return first column whose normalized name equals/contains an alias."""
    norms = {normalize_header(c): c for c in columns}
    alias_norms = [normalize_header(a) for a in aliases]
    for alias in alias_norms:
        if alias in norms:
            return norms[alias]
    for alias in alias_norms:
        if len(alias) < 4:
            continue
        for norm, original in norms.items():
            if alias in norm:
                return original
    return None


def pick_money(row: Mapping[str, Any], columns: Sequence[str], aliases: Sequence[str]) -> Decimal:
    col = find_column(columns, aliases)
    if col is None:
        return Decimal("0")
    return money(row.get(col))


def present_components(components: Mapping[str, Decimal]) -> dict[str, float]:
    return {k: float(v.quantize(Decimal("0.01"))) for k, v in components.items() if v != 0}
