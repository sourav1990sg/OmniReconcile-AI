"""Domain models for the Upload Intelligence Layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PlatformKind(str, Enum):
    """Detected upload platform (schema-driven)."""

    PETPOOJA = "petpooja"
    SWIGGY = "swiggy"
    ZOMATO = "zomato"
    UNKNOWN = "unknown"


class PreviewStatus(str, Enum):
    """Per-file preview gate before commit."""

    READY = "READY"
    WARNING = "WARNING"
    FAILED = "FAILED"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DatasetRole(str, Enum):
    """How a file participates in the staged workflow."""

    POS = "pos"
    SETTLEMENT = "settlement"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ValidationFinding:
    """One validation finding with severity (never swallowed)."""

    code: str
    message: str
    severity: Severity
    filename: str | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "filename": self.filename,
            "field": self.field,
        }


@dataclass(frozen=True)
class DetectionCandidate:
    """Score for one platform profile against a file's columns."""

    platform: PlatformKind
    confidence: float  # 0.0 – 1.0
    confidence_pct: int  # 0 – 100
    matched: bool
    column_map: dict[str, str]
    missing_required: tuple[str, ...]
    reasons: tuple[str, ...]
    source: str
    currency: str
    dataset_role: DatasetRole

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.value,
            "confidence": self.confidence,
            "confidence_pct": self.confidence_pct,
            "matched": self.matched,
            "column_map": dict(self.column_map),
            "missing_required": list(self.missing_required),
            "reasons": list(self.reasons),
            "source": self.source,
            "currency": self.currency,
            "dataset_role": self.dataset_role.value,
        }


@dataclass
class FilePreview:
    """Upload preview card payload (shown before import)."""

    filename: str
    platform: PlatformKind
    confidence_pct: int
    status: PreviewStatus
    dataset_role: DatasetRole
    rows: int = 0
    cancelled_orders: int = 0
    eligible_orders: int = 0
    duplicate_orders: int = 0
    date_from: str | None = None
    date_to: str | None = None
    outlets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    findings: list[ValidationFinding] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    column_map: dict[str, str] = field(default_factory=dict)
    checksum: str = ""
    currency: str = "INR"
    source: str = ""
    candidates: list[DetectionCandidate] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "platform": self.platform.value,
            "confidence_pct": self.confidence_pct,
            "status": self.status.value,
            "dataset_role": self.dataset_role.value,
            "rows": self.rows,
            "cancelled_orders": self.cancelled_orders,
            "eligible_orders": self.eligible_orders,
            "duplicate_orders": self.duplicate_orders,
            "date_range": {"from": self.date_from, "to": self.date_to},
            "outlets": list(self.outlets),
            "warnings": list(self.warnings),
            "findings": [f.to_dict() for f in self.findings],
            "reasons": list(self.reasons),
            "column_map": dict(self.column_map),
            "checksum": self.checksum,
            "currency": self.currency,
            "source": self.source,
            "candidates": [c.to_dict() for c in self.candidates],
        }


@dataclass(frozen=True)
class CoverageReport:
    """POS vs settlement date coverage (feeds business rules later)."""

    pos_from: str | None
    pos_to: str | None
    settlement_from: str | None
    settlement_to: str | None
    coverage_pct: float
    missing_from: str | None
    missing_to: str | None
    missing_days: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UploadHistoryEntry:
    """In-memory upload audit record."""

    upload_time: str
    uploaded_by: str
    session_id: str
    action: str
    files: list[str]
    rows: int
    platform: str
    date_from: str | None
    date_to: str | None
    checksums: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalyzeResult:
    """Result of analyzing one or many uploads without committing."""

    previews: list[FilePreview]
    pos_files: list[FilePreview]
    settlement_files: list[FilePreview]
    unknown_files: list[FilePreview]
    mixed_platforms: bool
    can_commit_pos: bool
    can_commit_settlement: bool
    findings: list[ValidationFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "previews": [p.to_dict() for p in self.previews],
            "pos_files": [p.to_dict() for p in self.pos_files],
            "settlement_files": [p.to_dict() for p in self.settlement_files],
            "unknown_files": [p.to_dict() for p in self.unknown_files],
            "mixed_platforms": self.mixed_platforms,
            "can_commit_pos": self.can_commit_pos,
            "can_commit_settlement": self.can_commit_settlement,
            "findings": [f.to_dict() for f in self.findings],
        }


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
