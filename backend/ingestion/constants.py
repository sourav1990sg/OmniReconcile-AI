"""
Ingestion constants.

Canonical field names live in ``backend.parsers.schemas.canonical``.
Petpooja aliases live in ``backend.parsers.schemas.petpooja_schema``.

This module re-exports shared symbols for Sprint-1 import compatibility.
"""

from __future__ import annotations

from backend.ingestion.loader import SUPPORTED_EXTENSIONS
from backend.parsers.schemas.canonical import (
    CANONICAL_AMOUNT,
    CANONICAL_COLUMNS,
    CANONICAL_DATE,
    CANONICAL_ORDER_ID,
    CANONICAL_OUTLET,
    CANONICAL_PLATFORM,
    CANONICAL_POS_INVOICE,
    CANONICAL_SOURCE_FILE,
    CANONICAL_STATUS,
)
from backend.parsers.schemas.petpooja_schema import (
    CANCELLED_STATUS_TOKENS,
    COLUMN_ALIASES,
    FILENAME_HINTS as PETPOOJA_FILENAME_HINTS,
    PREFERRED_EXACT,
    REQUIRED_ROLES,
)

__all__ = [
    "CANCELLED_STATUS_TOKENS",
    "CANONICAL_AMOUNT",
    "CANONICAL_COLUMNS",
    "CANONICAL_DATE",
    "CANONICAL_ORDER_ID",
    "CANONICAL_OUTLET",
    "CANONICAL_PLATFORM",
    "CANONICAL_POS_INVOICE",
    "CANONICAL_SOURCE_FILE",
    "CANONICAL_STATUS",
    "COLUMN_ALIASES",
    "PETPOOJA_FILENAME_HINTS",
    "PREFERRED_EXACT",
    "REQUIRED_ROLES",
    "SUPPORTED_EXTENSIONS",
]
