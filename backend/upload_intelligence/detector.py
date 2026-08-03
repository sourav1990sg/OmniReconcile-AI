"""
Column-based file detection (no filename dependency).

Uses existing schema aliases via ``map_columns``. Files that do not reach the
confidence threshold are classified as UNKNOWN_FILE and must not be parsed.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from backend.ingestion.loader import FileLoader
from backend.ingestion.logging_utils import log_with_context
from backend.parsers.column_mapper import map_columns, normalize_header
from backend.upload_intelligence.confidence import ConfidenceEngine
from backend.upload_intelligence.models import (
    DatasetRole,
    DetectionCandidate,
    PlatformKind,
    Severity,
    ValidationFinding,
)
from backend.upload_intelligence.profiles import DetectionProfile, build_profiles

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedFrame:
    """Raw frame used for detection / preview (may be empty)."""

    dataframe: pd.DataFrame
    load_error: str | None = None
    sheet_name: str | None = None


@dataclass(frozen=True)
class FileDetectionResult:
    """Winner + all candidates for one uploaded file."""

    filename: str
    winner: DetectionCandidate
    candidates: tuple[DetectionCandidate, ...]
    frame: LoadedFrame
    findings: tuple[ValidationFinding, ...]

    @property
    def is_unknown(self) -> bool:
        return self.winner.platform == PlatformKind.UNKNOWN or not self.winner.matched


class ColumnFileDetector:
    """
    Detect platform from column names only.

    SOLID: profiles and confidence engine are injectable.
    """

    def __init__(
        self,
        profiles: Sequence[DetectionProfile] | None = None,
        confidence: ConfidenceEngine | None = None,
        loader: FileLoader | None = None,
    ) -> None:
        self._profiles = tuple(profiles) if profiles is not None else build_profiles()
        self._confidence = confidence or ConfidenceEngine()
        self._loader = loader or FileLoader()

    def detect(self, filename: str, content: bytes) -> FileDetectionResult:
        findings: list[ValidationFinding] = []

        if not content:
            unknown = self._confidence.unknown_candidate(
                reasons=("Empty file",),
                confidence=0.0,
            )
            findings.append(
                ValidationFinding(
                    code="empty_file",
                    message=f"File '{filename}' is empty",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return FileDetectionResult(
                filename=filename,
                winner=unknown,
                candidates=(unknown,),
                frame=LoadedFrame(pd.DataFrame(), load_error="empty"),
                findings=tuple(findings),
            )

        if not self._loader.is_supported_filename(filename):
            unknown = self._confidence.unknown_candidate(
                reasons=("Unsupported extension",),
                confidence=0.05,
            )
            findings.append(
                ValidationFinding(
                    code="unsupported_extension",
                    message=f"Unsupported file extension for '{filename}'",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return FileDetectionResult(
                filename=filename,
                winner=unknown,
                candidates=(unknown,),
                frame=LoadedFrame(pd.DataFrame(), load_error="unsupported"),
                findings=tuple(findings),
            )

        frame = self._load_best_frame(filename, content)
        if frame.load_error and frame.dataframe.empty:
            unknown = self._confidence.unknown_candidate(
                reasons=(f"Unreadable file: {frame.load_error}",),
                confidence=0.0,
            )
            findings.append(
                ValidationFinding(
                    code="unreadable_file",
                    message=f"Could not read '{filename}': {frame.load_error}",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return FileDetectionResult(
                filename=filename,
                winner=unknown,
                candidates=(unknown,),
                frame=frame,
                findings=tuple(findings),
            )

        if frame.dataframe.empty and not list(frame.dataframe.columns):
            unknown = self._confidence.unknown_candidate(
                reasons=("Empty spreadsheet (no columns)",),
                confidence=0.0,
            )
            findings.append(
                ValidationFinding(
                    code="empty_file",
                    message=f"File '{filename}' has no columns",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return FileDetectionResult(
                filename=filename,
                winner=unknown,
                candidates=(unknown,),
                frame=frame,
                findings=tuple(findings),
            )

        columns = [str(c) for c in frame.dataframe.columns]
        candidates: list[DetectionCandidate] = []
        for profile in self._profiles:
            column_map = map_columns(
                frame.dataframe.columns,
                aliases=profile.column_aliases,
                preferred_exact=profile.preferred_exact,
            )
            column_map = self._prefer_distinctive(profile, columns, column_map)
            candidates.append(self._confidence.score(profile, column_map, columns))

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        matched = [c for c in candidates if c.matched]
        if matched:
            winner = self._break_ties(matched, columns)
            winner = self._guard_cross_platform(winner, matched, columns, findings, filename)
            # Ambiguous: two matched platforms within 5%
            close = [
                c
                for c in matched
                if abs(c.confidence - winner.confidence) < 0.05 and c.platform != winner.platform
            ]
            if close and winner.matched:
                findings.append(
                    ValidationFinding(
                        code="ambiguous_platform",
                        message=(
                            f"Close scores between {winner.platform.value} "
                            f"and {close[0].platform.value}; chose {winner.platform.value} "
                            "via distinctive columns"
                        ),
                        severity=Severity.WARNING,
                        filename=filename,
                    )
                )
        else:
            best = candidates[0] if candidates else None
            low_conf = (best.confidence if best else 0.12)
            reasons = (
                "UNKNOWN_FILE: no platform reached confidence threshold",
                *(best.reasons if best else ()),
            )
            winner = self._confidence.unknown_candidate(reasons=reasons, confidence=min(0.25, low_conf))
            findings.append(
                ValidationFinding(
                    code="unknown_file",
                    message="UNKNOWN_FILE — do not parse; columns did not match any known schema",
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )

        log_with_context(
            logger,
            logging.INFO,
            "Column detection complete",
            filename=filename,
            platform=winner.platform.value,
            confidence_pct=winner.confidence_pct,
            matched=winner.matched,
        )
        return FileDetectionResult(
            filename=filename,
            winner=winner,
            candidates=tuple(candidates),
            frame=frame,
            findings=tuple(findings),
        )

    def _load_best_frame(self, filename: str, content: bytes) -> LoadedFrame:
        """Load CSV/Excel; for Excel try sheet hints and header rediscovery."""
        lower = (filename or "").lower()
        try:
            if lower.endswith(".csv"):
                df = self._loader.load(filename, content)
                return LoadedFrame(df)
        except Exception as exc:  # noqa: BLE001
            return LoadedFrame(pd.DataFrame(), load_error=str(exc))

        # Excel: try default, then sheet hints with header discovery, then global header scan
        errors: list[str] = []
        try:
            df = self._loader.load(filename, content)
            if self._any_profile_matches(df):
                return LoadedFrame(df)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            df = pd.DataFrame()

        for sheet in self._all_sheet_hints():
            try:
                discovered = self._discover_sheet_header(content, sheet)
                if discovered is not None and self._any_profile_matches(discovered):
                    return LoadedFrame(discovered, sheet_name=sheet)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"sheet '{sheet}': {exc}")

        # Header rediscovery on first sheet using column match callback
        try:
            discovered = self._loader.discover_header_frame(
                content,
                filename,
                is_match=lambda probe, _name: self._any_profile_matches(probe),
            )
            if discovered is not None:
                return LoadedFrame(discovered)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        # Last resort: scan all sheets for a matching header row
        try:
            xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
            for sheet in xl.sheet_names:
                discovered = self._discover_sheet_header(content, sheet)
                if discovered is not None and self._any_profile_matches(discovered):
                    return LoadedFrame(discovered, sheet_name=sheet)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        if not df.empty or list(df.columns):
            return LoadedFrame(df)
        return LoadedFrame(pd.DataFrame(), load_error="; ".join(errors) or "unreadable")

    def _discover_sheet_header(self, content: bytes, sheet: str) -> pd.DataFrame | None:
        """Find header row by column names within a named Excel sheet."""
        try:
            preview = pd.read_excel(
                io.BytesIO(content),
                sheet_name=sheet,
                header=None,
                nrows=40,
                engine="openpyxl",
            )
        except Exception:  # noqa: BLE001
            return None

        header_idx: int | None = None
        for idx, row in preview.iterrows():
            values = [str(v) for v in row.tolist() if pd.notna(v)]
            if len(values) < 2:
                continue
            probe = pd.DataFrame(columns=values)
            if self._any_profile_matches(probe):
                header_idx = int(idx)
                break

        if header_idx is None:
            return None

        return pd.read_excel(
            io.BytesIO(content),
            sheet_name=sheet,
            header=header_idx,
            engine="openpyxl",
        )
    def _any_profile_matches(self, df: pd.DataFrame) -> bool:
        if df is None or (df.empty and not list(df.columns)):
            return False
        columns = [str(c) for c in df.columns]
        for profile in self._profiles:
            column_map = map_columns(
                df.columns,
                aliases=profile.column_aliases,
                preferred_exact=profile.preferred_exact,
            )
            candidate = self._confidence.score(profile, column_map, columns)
            if candidate.matched:
                return True
        return False

    def _break_ties(
        self,
        matched: list[DetectionCandidate],
        columns: list[str],
    ) -> DetectionCandidate:
        """Prefer the profile with the strongest distinctive header hits."""
        if len(matched) == 1:
            return matched[0]
        norms = {normalize_header(c) for c in columns}
        profile_by_platform = {p.platform: p for p in self._profiles}

        def score(candidate: DetectionCandidate) -> tuple[float, int, float]:
            profile = profile_by_platform.get(candidate.platform)
            distinctive = 0
            if profile:
                for alias in profile.distinctive_aliases:
                    a = normalize_header(alias)
                    if a in norms or any(a in n and len(a) >= 8 for n in norms):
                        distinctive += 1
            return (candidate.confidence, distinctive, candidate.confidence)

        return max(matched, key=score)

    def _guard_cross_platform(
        self,
        winner: DetectionCandidate,
        matched: list[DetectionCandidate],
        columns: list[str],
        findings: list[ValidationFinding],
        filename: str,
    ) -> DetectionCandidate:
        """
        Prevent Swiggy/Zomato settlement schemas from being labeled Petpooja (or vice versa).
        Schema markers only — never filenames.
        """
        norms = {normalize_header(c) for c in columns}
        has_swiggy = any("net payable" in n for n in norms) or "rid" in norms
        has_zomato = any("order level payout" in n for n in norms)
        has_petpooja = any(
            n in {"my amount", "expected amount"} or "aggregator order no" in n for n in norms
        )

        if winner.platform == PlatformKind.PETPOOJA and (has_swiggy or has_zomato) and not has_petpooja:
            alt = next(
                (
                    c
                    for c in matched
                    if c.platform
                    in {PlatformKind.SWIGGY, PlatformKind.ZOMATO}
                    and c.matched
                ),
                None,
            )
            if alt:
                findings.append(
                    ValidationFinding(
                        code="platform_guard_reclassified",
                        message=(
                            f"Reclassified from Petpooja to {alt.platform.value} "
                            "using settlement schema markers (RID / Net Payable / Order level Payout)"
                        ),
                        severity=Severity.WARNING,
                        filename=filename,
                    )
                )
                return alt
            findings.append(
                ValidationFinding(
                    code="platform_guard_rejected",
                    message=(
                        "Rejected Petpooja classification: settlement schema markers present "
                        "without Petpooja required columns. Confidence below enterprise threshold."
                    ),
                    severity=Severity.ERROR,
                    filename=filename,
                )
            )
            return self._confidence.unknown_candidate(
                reasons=(
                    "Cross-platform guard: settlement columns detected without Petpooja markers",
                    *winner.reasons,
                ),
                confidence=min(0.5, winner.confidence),
            )

        if winner.platform in {PlatformKind.SWIGGY, PlatformKind.ZOMATO} and has_petpooja and not (
            has_swiggy or has_zomato
        ):
            alt = next((c for c in matched if c.platform == PlatformKind.PETPOOJA and c.matched), None)
            if alt:
                findings.append(
                    ValidationFinding(
                        code="platform_guard_reclassified",
                        message=f"Reclassified from {winner.platform.value} to Petpooja using POS schema markers",
                        severity=Severity.WARNING,
                        filename=filename,
                    )
                )
                return alt

        return winner

    def _all_sheet_hints(self) -> tuple[str, ...]:
        hints: list[str] = []
        for p in self._profiles:
            for s in p.sheet_hints:
                if s not in hints:
                    hints.append(s)
        return tuple(hints)

    @staticmethod
    def _prefer_distinctive(
        profile: DetectionProfile,
        columns: list[str],
        column_map: dict[str, str],
    ) -> dict[str, str]:
        """Prefer distinctive amount columns (e.g. Order level Payout over bare 'payout')."""
        if not profile.distinctive_aliases:
            return column_map
        role_to_source = {role: src for src, role in column_map.items()}
        amount_roles = ("amount", "settled_amount")
        target_role = next((r for r in amount_roles if r in role_to_source), None)
        if target_role is None:
            return column_map

        # Only amount/payout-like distinctive headers — never order-id headers
        amount_tokens = ("amount", "payout", "payable")
        amount_aliases = [
            a
            for a in profile.distinctive_aliases
            if any(tok in normalize_header(a) for tok in amount_tokens)
        ]
        if not amount_aliases:
            return column_map

        norms = {normalize_header(c): c for c in columns}
        for alias in amount_aliases:
            a = normalize_header(alias)
            for norm, original in norms.items():
                if norm == a or (a in norm and len(a) >= 8):
                    new_map = {src: role for src, role in column_map.items() if role != target_role}
                    new_map[original] = target_role
                    return new_map
        return column_map
