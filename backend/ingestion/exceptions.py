"""
Exceptions for the POS ingestion engine.

Reserved for callers that prefer exception-driven control flow.
Validation findings are primarily returned via :class:`ValidationIssue`.
"""

from __future__ import annotations


class IngestionError(Exception):
    """Base error for the ingestion engine."""


class UnsupportedFileError(IngestionError):
    """Raised when a file type cannot be ingested."""


class InvalidPetpoojaFileError(IngestionError):
    """Raised when a file fails Petpooja validation and skipping is disabled."""
