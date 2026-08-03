"""
Parser-agnostic file detection.

Detection delegates to the :class:`ParserRegistry`; Petpooja-specific aliases
live under ``backend.parsers.schemas``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from backend.ingestion.loader import SUPPORTED_EXTENSIONS, FileLoader
from backend.ingestion.logging_utils import log_with_context
from backend.parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionResult:
    """Outcome of source detection for one raw table."""

    matched: bool
    platform: str | None
    source: str | None
    parser_id: str | None
    column_map: dict[str, str]
    confidence: float
    reasons: tuple[str, ...]
    currency: str = "INR"

    @property
    def is_petpooja(self) -> bool:
        """Backward-compatible flag used by Sprint-1 tests/callers."""
        return bool(self.matched and self.platform == "petpooja")


class FileDetector:
    """Detect which registered parser can handle a raw DataFrame."""

    def __init__(self, registry: ParserRegistry | None = None) -> None:
        self._registry = registry or ParserRegistry()
        self._loader = FileLoader()

    @property
    def registry(self) -> ParserRegistry:
        return self._registry

    def detect_from_dataframe(
        self,
        df: pd.DataFrame,
        filename: str | None = None,
    ) -> DetectionResult:
        parser, detection = self._registry.detect(df, filename)
        if parser is None or detection is None:
            result = DetectionResult(
                matched=False,
                platform=None,
                source=None,
                parser_id=None,
                column_map={},
                confidence=0.0,
                reasons=("No registered parser matched this file",),
            )
        else:
            result = DetectionResult(
                matched=True,
                platform=detection.platform,
                source=detection.source,
                parser_id=parser.parser_id,
                column_map=detection.column_map,
                confidence=detection.confidence,
                reasons=detection.reasons,
                currency=detection.currency,
            )

        log_with_context(
            logger,
            logging.DEBUG,
            "Detection complete",
            filename=filename or "<memory>",
            matched=result.matched,
            platform=result.platform,
            confidence=result.confidence,
        )
        return result

    def is_supported_filename(self, filename: str | None) -> bool:
        return self._loader.is_supported_filename(filename)


class PetpoojaReportDetector(FileDetector):
    """
    Sprint-1 compatible detector facade.

    Behaviourally identical for Petpooja files; implemented via the registry.
    """

    def map_columns(self, columns: pd.Index | list[str]) -> dict[str, str]:
        """Map columns using the Petpooja parser's schema."""
        parser = self._registry.get("petpooja")
        if parser is None:
            return {}
        probe = pd.DataFrame(columns=list(columns))
        return parser.detect(probe).column_map
