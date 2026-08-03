"""Route detected uploads to the appropriate source parser."""

from __future__ import annotations

import logging

import pandas as pd

from backend.ingestion.detector import DetectionResult
from backend.ingestion.logging_utils import log_with_context
from backend.parsers.base import ParseResult, SourceParser
from backend.parsers.registry import ParserRegistry

logger = logging.getLogger(__name__)


class ParserRouter:
    """Resolve a :class:`DetectionResult` to a :class:`SourceParser` and parse."""

    def __init__(self, registry: ParserRegistry | None = None) -> None:
        self._registry = registry or ParserRegistry()

    def resolve(self, detection: DetectionResult) -> SourceParser | None:
        if not detection.matched or not detection.parser_id:
            return None
        return self._registry.get(detection.parser_id)

    def parse(
        self,
        df: pd.DataFrame,
        detection: DetectionResult,
        *,
        source_file: str,
    ) -> ParseResult:
        parser = self.resolve(detection)
        if parser is None:
            raise ValueError(f"No parser registered for detection of '{source_file}'")

        log_with_context(
            logger,
            logging.INFO,
            "Routing file to parser",
            filename=source_file,
            parser_id=parser.parser_id,
            platform=parser.platform,
        )
        return parser.parse(df, detection.column_map, source_file=source_file)
