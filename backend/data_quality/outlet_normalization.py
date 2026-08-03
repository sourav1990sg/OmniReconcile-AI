"""
Outlet Normalization Layer (Sprint 9).

Maps platform store IDs / alternate labels to canonical outlet names.
Does not alter financial formulas — display / aggregation key hygiene only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


_MAP_PATH = Path(__file__).with_name("outlet_map.json")


@dataclass(frozen=True)
class OutletResolution:
    """Result of normalizing a raw outlet / RID value."""

    display_name: str
    mapped: bool
    original: str
    recommendation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "mapped": self.mapped,
            "original": self.original,
            "recommendation": self.recommendation,
        }


@lru_cache(maxsize=1)
def _load_map() -> dict[str, str]:
    if not _MAP_PATH.exists():
        return {}
    payload = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
    raw = payload.get("mappings") or {}
    return {str(k).strip().lower(): str(v).strip() for k, v in raw.items() if str(v).strip()}


def resolve_outlet(value: Any) -> OutletResolution:
    """
    Resolve raw outlet / RID to canonical name.

    Never returns the literal string \"Unknown\".
    Unmapped values become \"Outlet Not Mapped\" with guidance.
    """
    original = str(value or "").strip()
    if not original or original in {"—", "-", "N/A", "n/a", "null", "None"}:
        return OutletResolution(
            display_name="Outlet Not Mapped",
            mapped=False,
            original=original or "(empty)",
            recommendation="Provide POS Outlet Name or add RID mapping in outlet_map.json.",
        )

    key = original.lower()
    mapping = _load_map()
    if key in mapping:
        return OutletResolution(
            display_name=mapping[key],
            mapped=True,
            original=original,
            recommendation=None,
        )

    # Numeric RID with no map
    if original.isdigit():
        return OutletResolution(
            display_name="Outlet Not Mapped",
            mapped=False,
            original=original,
            recommendation=f"Map RID {original} to a canonical outlet in outlet_map.json.",
        )

    # Already a human label — keep as-is (canonical)
    if original.lower() not in {"unknown", "n/a"}:
        return OutletResolution(
            display_name=original,
            mapped=True,
            original=original,
            recommendation=None,
        )

    return OutletResolution(
        display_name="Outlet Not Mapped",
        mapped=False,
        original=original,
        recommendation="Replace Unknown with a canonical outlet mapping.",
    )


def canonical_outlet_name(value: Any) -> str:
    """Convenience: display string only."""
    return resolve_outlet(value).display_name


__all__ = ["OutletResolution", "resolve_outlet", "canonical_outlet_name"]
