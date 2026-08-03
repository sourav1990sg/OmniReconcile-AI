"""
Parser-agnostic Data Ingestion Engine.

Performs file loading, detection, validation, and routing to source parsers.
Does **not** perform reconciliation, AI, reporting, or export.
"""

from backend.ingestion.models import (
    CanonicalDataset,
    CanonicalOrder,
    DateRange,
    DatasetMetadata,
    IngestionResult,
)
from backend.ingestion.upload_service import PosUploadService, UploadedFile

__all__ = [
    "CanonicalDataset",
    "CanonicalOrder",
    "DateRange",
    "DatasetMetadata",
    "IngestionResult",
    "PosUploadService",
    "UploadedFile",
]
