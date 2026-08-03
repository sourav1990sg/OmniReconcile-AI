"""
Session protection for staged uploads.

Once POS succeeds it is locked. Settlement must never overwrite POS.
Replace requires an explicit replace action (new session).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from backend.pipeline.orchestrator import PipelineSession, _SESSIONS, get_or_create_session
from backend.upload_intelligence.coverage import compute_coverage
from backend.upload_intelligence.models import (
    CoverageReport,
    FilePreview,
    UploadHistoryEntry,
    utc_now_iso,
)


class SessionLockedError(Exception):
    """Raised when POS is locked and replace was not requested."""

    def __init__(self, session_id: str, message: str | None = None) -> None:
        self.session_id = session_id
        super().__init__(
            message
            or (
                f"POS dataset is locked on session '{session_id}'. "
                "Click Replace POS Dataset to create a new session."
            )
        )


class UploadSessionManager:
    """
    Protects staged sessions and records upload history (in-memory).

    Extends PipelineSession fields introduced in Sprint 5A.
    """

    def get(self, session_id: str) -> PipelineSession:
        if session_id not in _SESSIONS:
            raise KeyError(session_id)
        return _SESSIONS[session_id]

    def get_or_create(self, session_id: str | None = None) -> PipelineSession:
        return get_or_create_session(session_id)

    def ensure_extended(self, session: PipelineSession) -> PipelineSession:
        """Backfill Sprint 5A fields on older session objects."""
        if not hasattr(session, "pos_locked"):
            session.pos_locked = False  # type: ignore[attr-defined]
        if not hasattr(session, "upload_history"):
            session.upload_history = []  # type: ignore[attr-defined]
        if not hasattr(session, "pos_previews"):
            session.pos_previews = []  # type: ignore[attr-defined]
        if not hasattr(session, "settlement_previews"):
            session.settlement_previews = []  # type: ignore[attr-defined]
        if not hasattr(session, "coverage"):
            session.coverage = None  # type: ignore[attr-defined]
        if not hasattr(session, "uploaded_by"):
            session.uploaded_by = "operator"  # type: ignore[attr-defined]
        return session

    def assert_pos_writable(self, session: PipelineSession, *, replace: bool = False) -> None:
        session = self.ensure_extended(session)
        if session.pos_locked and session.pos_files and not replace:
            raise SessionLockedError(session.session_id)

    def commit_pos(
        self,
        session: PipelineSession,
        *,
        files: list[tuple[str, bytes]],
        summary: dict[str, Any],
        previews: list[FilePreview],
        uploaded_by: str = "operator",
        replace: bool = False,
    ) -> PipelineSession:
        session = self.ensure_extended(session)
        self.assert_pos_writable(session, replace=replace)

        if replace and session.pos_locked:
            # Caller should prefer replace_pos(); keep defensive clear
            session.pos_files = []
            session.settlement_files = []
            session.settlement_summary = None
            session.settlement_previews = []
            session.coverage = None

        session.pos_files = list(files)
        session.pos_summary = summary
        session.pos_previews = [p.to_dict() for p in previews]
        session.pos_locked = True
        session.uploaded_by = uploaded_by
        self._history(
            session,
            action="pos_replace" if replace else "pos_upload",
            files=[n for n, _ in files],
            rows=int(summary.get("total_orders") or 0),
            platform=str(summary.get("platform") or "petpooja"),
            date_from=(summary.get("date_range") or {}).get("from"),
            date_to=(summary.get("date_range") or {}).get("to"),
            checksums=[p.checksum for p in previews],
            uploaded_by=uploaded_by,
        )
        self.refresh_coverage(session)
        return session

    def commit_settlement(
        self,
        session: PipelineSession,
        *,
        files: list[tuple[str, bytes]],
        summary: dict[str, Any],
        previews: list[FilePreview],
        uploaded_by: str = "operator",
    ) -> PipelineSession:
        """Settlement never overwrites POS files or lock."""
        session = self.ensure_extended(session)
        if not session.pos_files or not session.pos_locked:
            raise ValueError("Upload and lock POS before settlement.")

        # Append/replace settlement only — POS untouched
        session.settlement_files = list(files)
        session.settlement_summary = summary
        session.settlement_previews = [p.to_dict() for p in previews]
        self._history(
            session,
            action="settlement_upload",
            files=[n for n, _ in files],
            rows=int(summary.get("total_orders") or 0),
            platform=",".join(summary.get("platforms") or [summary.get("platform") or ""]),
            date_from=(summary.get("date_range") or {}).get("from"),
            date_to=(summary.get("date_range") or {}).get("to"),
            checksums=[p.checksum for p in previews],
            uploaded_by=uploaded_by,
        )
        self.refresh_coverage(session)
        return session

    def replace_pos(self, old_session_id: str | None = None) -> PipelineSession:
        """
        Explicit POS replace: drop old session (if provided) and create a fresh one.
        """
        if old_session_id and old_session_id in _SESSIONS:
            del _SESSIONS[old_session_id]
        new_id = str(uuid4())
        session = get_or_create_session(new_id)
        return self.ensure_extended(session)

    def refresh_coverage(self, session: PipelineSession) -> CoverageReport | None:
        session = self.ensure_extended(session)
        pos = session.pos_summary or {}
        settle = session.settlement_summary or {}
        pos_range = pos.get("date_range") or {}
        settle_range = settle.get("date_range") or {}
        if not pos:
            session.coverage = None
            return None
        report = compute_coverage(
            pos_from=pos_range.get("from"),
            pos_to=pos_range.get("to"),
            settlement_from=settle_range.get("from") if settle else None,
            settlement_to=settle_range.get("to") if settle else None,
        )
        session.coverage = report.to_dict()
        return report

    def snapshot(self, session: PipelineSession) -> dict[str, Any]:
        session = self.ensure_extended(session)
        return {
            "session_id": session.session_id,
            "pos_locked": bool(session.pos_locked),
            "has_pos": bool(session.pos_files),
            "has_settlement": bool(session.settlement_files),
            "pos_summary": session.pos_summary,
            "settlement_summary": session.settlement_summary,
            "pos_previews": list(getattr(session, "pos_previews", []) or []),
            "settlement_previews": list(getattr(session, "settlement_previews", []) or []),
            "coverage": getattr(session, "coverage", None),
            "upload_history": list(getattr(session, "upload_history", []) or []),
            "uploaded_by": getattr(session, "uploaded_by", "operator"),
        }

    def _history(
        self,
        session: PipelineSession,
        *,
        action: str,
        files: list[str],
        rows: int,
        platform: str,
        date_from: str | None,
        date_to: str | None,
        checksums: list[str],
        uploaded_by: str,
    ) -> None:
        entry = UploadHistoryEntry(
            upload_time=utc_now_iso(),
            uploaded_by=uploaded_by,
            session_id=session.session_id,
            action=action,
            files=files,
            rows=rows,
            platform=platform,
            date_from=date_from,
            date_to=date_to,
            checksums=checksums,
        )
        history = list(getattr(session, "upload_history", []) or [])
        history.append(entry.to_dict())
        session.upload_history = history
