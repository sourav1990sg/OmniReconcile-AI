"""
Upload Intelligence façade — analyze + gate commits without rewriting ingest.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from backend.upload_intelligence.detector import ColumnFileDetector
from backend.upload_intelligence.models import (
    AnalyzeResult,
    DatasetRole,
    FilePreview,
    PlatformKind,
    PreviewStatus,
    Severity,
    ValidationFinding,
)
from backend.upload_intelligence.preview import PreviewBuilder
from backend.upload_intelligence.session_manager import UploadSessionManager
from backend.upload_intelligence.validator import UploadValidator


class UploadIntelligenceService:
    """
    Orchestrates detect → confidence → validate → preview.

    Actual POS/settlement ingest remains in existing upload services.
    """

    def __init__(
        self,
        *,
        reference_date: date | None = None,
        detector: ColumnFileDetector | None = None,
        preview: PreviewBuilder | None = None,
        validator: UploadValidator | None = None,
        sessions: UploadSessionManager | None = None,
    ) -> None:
        self._as_of = reference_date or date.today()
        self._detector = detector or ColumnFileDetector()
        self._validator = validator or UploadValidator(reference_date=self._as_of)
        self._preview = preview or PreviewBuilder(
            detector=self._detector,
            validator=self._validator,
            reference_date=self._as_of,
        )
        self._sessions = sessions or UploadSessionManager()

    @property
    def sessions(self) -> UploadSessionManager:
        return self._sessions

    def analyze(self, files: Sequence[tuple[str, bytes]]) -> AnalyzeResult:
        previews = [self._preview.build(name, content) for name, content in files]
        batch_findings = self._validator.validate_batch(previews)
        for f in batch_findings:
            # Attach batch findings to result only (not mutate every preview)
            pass

        pos = [
            p
            for p in previews
            if p.dataset_role == DatasetRole.POS and p.platform == PlatformKind.PETPOOJA
        ]
        settlement = [
            p
            for p in previews
            if p.dataset_role == DatasetRole.SETTLEMENT
            and p.platform in (PlatformKind.SWIGGY, PlatformKind.ZOMATO)
        ]
        unknown = [
            p
            for p in previews
            if p.platform == PlatformKind.UNKNOWN or p.status == PreviewStatus.FAILED
        ]

        # Mixed: POS+settlement in one drop is OK for routing; mixed POS platforms is not
        mixed = any(f.code == "mixed_platforms" for f in batch_findings)

        can_pos = bool(pos) and all(p.status != PreviewStatus.FAILED for p in pos) and not mixed
        can_settle = bool(settlement) and all(
            p.status != PreviewStatus.FAILED for p in settlement
        )

        return AnalyzeResult(
            previews=previews,
            pos_files=pos,
            settlement_files=settlement,
            unknown_files=unknown,
            mixed_platforms=mixed,
            can_commit_pos=can_pos,
            can_commit_settlement=can_settle,
            findings=batch_findings,
        )

    def partition_for_commit(
        self,
        files: Sequence[tuple[str, bytes]],
        *,
        role: DatasetRole,
    ) -> tuple[list[tuple[str, bytes]], list[FilePreview], list[ValidationFinding]]:
        """
        Filter uploads to those matching ``role`` with non-FAILED status.

        UNKNOWN / wrong-role files are reported as findings and excluded.
        """
        analysis = self.analyze(files)
        accepted: list[tuple[str, bytes]] = []
        previews: list[FilePreview] = []
        findings: list[ValidationFinding] = list(analysis.findings)
        by_name = {name: content for name, content in files}

        target = analysis.pos_files if role == DatasetRole.POS else analysis.settlement_files
        for preview in target:
            if preview.status == PreviewStatus.FAILED:
                findings.append(
                    ValidationFinding(
                        code="failed_preview",
                        message=f"Excluding failed file '{preview.filename}'",
                        severity=Severity.ERROR,
                        filename=preview.filename,
                    )
                )
                continue
            content = by_name.get(preview.filename)
            if content is None:
                continue
            accepted.append((preview.filename, content))
            previews.append(preview)

        for preview in analysis.unknown_files:
            if preview in target:
                continue
            findings.append(
                ValidationFinding(
                    code="unknown_file",
                    message=f"UNKNOWN_FILE excluded from {role.value} commit: '{preview.filename}'",
                    severity=Severity.ERROR,
                    filename=preview.filename,
                )
            )

        # Wrong role in the same batch
        other = analysis.settlement_files if role == DatasetRole.POS else analysis.pos_files
        for preview in other:
            findings.append(
                ValidationFinding(
                    code="wrong_dataset_role",
                    message=(
                        f"File '{preview.filename}' detected as {preview.platform.value} "
                        f"({preview.dataset_role.value}) — not committed as {role.value}"
                    ),
                    severity=Severity.WARNING,
                    filename=preview.filename,
                )
            )

        return accepted, previews, findings

    def analyze_dict(self, files: Sequence[tuple[str, bytes]]) -> dict[str, Any]:
        return self.analyze(files).to_dict()
