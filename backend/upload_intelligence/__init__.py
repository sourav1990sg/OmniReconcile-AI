"""
Upload Intelligence Layer (Sprint 5A).

Column-based detection, confidence scoring, preview, validation,
session protection, and coverage — without rewriting ingestion or reconciliation.
"""

from backend.upload_intelligence.confidence import ConfidenceEngine
from backend.upload_intelligence.detector import ColumnFileDetector
from backend.upload_intelligence.models import (
    CoverageReport,
    FilePreview,
    PlatformKind,
    PreviewStatus,
    Severity,
    UploadHistoryEntry,
    ValidationFinding,
)
from backend.upload_intelligence.preview import PreviewBuilder
from backend.upload_intelligence.service import UploadIntelligenceService
from backend.upload_intelligence.session_manager import UploadSessionManager
from backend.upload_intelligence.validator import UploadValidator

__all__ = [
    "ColumnFileDetector",
    "ConfidenceEngine",
    "CoverageReport",
    "FilePreview",
    "PlatformKind",
    "PreviewBuilder",
    "PreviewStatus",
    "Severity",
    "UploadHistoryEntry",
    "UploadIntelligenceService",
    "UploadSessionManager",
    "UploadValidator",
    "ValidationFinding",
]
