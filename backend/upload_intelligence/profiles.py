"""
Schema-driven detection profiles.

Profiles reference existing parser schemas — no hardcoded column indexes
or filenames. Matching is column-name only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from backend.parsers.schemas import petpooja_schema
from backend.parsers.swiggy import schema as swiggy_schema
from backend.parsers.zomato import schema as zomato_schema
from backend.upload_intelligence.models import DatasetRole, PlatformKind


@dataclass(frozen=True)
class DetectionProfile:
    """One platform's column schema for intelligence detection."""

    platform: PlatformKind
    source: str
    currency: str
    dataset_role: DatasetRole
    required_roles: tuple[str, ...]
    column_aliases: Mapping[str, Sequence[str]]
    preferred_exact: Mapping[str, Sequence[str]]
    optional_roles: tuple[str, ...] = ()
    # Distinctive preferred headers that strongly identify this platform
    distinctive_aliases: tuple[str, ...] = ()
    sheet_hints: tuple[str, ...] = ()


def build_profiles() -> tuple[DetectionProfile, ...]:
    """Build profiles from existing schema modules (single source of truth)."""
    petpooja_optional = tuple(
        role for role in petpooja_schema.COLUMN_ALIASES if role not in petpooja_schema.REQUIRED_ROLES
    )
    swiggy_optional = tuple(
        role for role in swiggy_schema.COLUMN_ALIASES if role not in swiggy_schema.REQUIRED_ROLES
    )
    zomato_optional = tuple(
        role for role in zomato_schema.COLUMN_ALIASES if role not in zomato_schema.REQUIRED_ROLES
    )

    return (
        DetectionProfile(
            platform=PlatformKind.PETPOOJA,
            source=petpooja_schema.SOURCE,
            currency=petpooja_schema.DEFAULT_CURRENCY,
            dataset_role=DatasetRole.POS,
            required_roles=petpooja_schema.REQUIRED_ROLES,
            column_aliases=petpooja_schema.COLUMN_ALIASES,
            preferred_exact=petpooja_schema.PREFERRED_EXACT,
            optional_roles=petpooja_optional,
            distinctive_aliases=(
                "aggregator order no",
                "aggregator order no.",
                "my amount",
                "petpooja identifier",
            ),
        ),
        DetectionProfile(
            platform=PlatformKind.SWIGGY,
            source=swiggy_schema.SOURCE,
            currency=swiggy_schema.DEFAULT_CURRENCY,
            dataset_role=DatasetRole.SETTLEMENT,
            required_roles=swiggy_schema.REQUIRED_ROLES,
            column_aliases=swiggy_schema.COLUMN_ALIASES,
            preferred_exact=swiggy_schema.PREFERRED_EXACT,
            optional_roles=swiggy_optional,
            distinctive_aliases=(
                "net payable amount (after tcs and tds deduction)",
                "net payable amount (after",
                "rid",
                "order no",
            ),
        ),
        DetectionProfile(
            platform=PlatformKind.ZOMATO,
            source=zomato_schema.SOURCE,
            currency=zomato_schema.DEFAULT_CURRENCY,
            dataset_role=DatasetRole.SETTLEMENT,
            required_roles=zomato_schema.REQUIRED_ROLES,
            column_aliases=zomato_schema.COLUMN_ALIASES,
            preferred_exact=zomato_schema.PREFERRED_EXACT,
            optional_roles=zomato_optional,
            distinctive_aliases=(
                "order level payout",
                "res. name",
                "commissionable value (after discount + packing chrg)",
            ),
            sheet_hints=(zomato_schema.ORDER_LEVEL_SHEET,),
        ),
    )
