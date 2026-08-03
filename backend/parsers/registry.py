"""Registry of source parsers for detection and routing."""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd

from backend.parsers.base import ParserDetection, SourceParser
from backend.parsers.petpooja import PetpoojaParser


class ParserRegistry:
    """
    Holds registered :class:`SourceParser` instances.

    Detection tries each parser and returns the highest-confidence match.
    """

    def __init__(self, parsers: Sequence[SourceParser] | None = None) -> None:
        self._parsers: list[SourceParser] = list(parsers) if parsers is not None else [PetpoojaParser()]

    def register(self, parser: SourceParser) -> None:
        self._parsers.append(parser)

    def all_parsers(self) -> tuple[SourceParser, ...]:
        return tuple(self._parsers)

    def get(self, parser_id: str) -> SourceParser | None:
        for parser in self._parsers:
            if parser.parser_id == parser_id:
                return parser
        return None

    def detect(
        self,
        df: pd.DataFrame,
        filename: str | None = None,
    ) -> tuple[SourceParser | None, ParserDetection | None]:
        """Return the best matching parser and its detection result."""
        best: tuple[SourceParser, ParserDetection] | None = None
        for parser in self._parsers:
            detection = parser.detect(df, filename)
            if not detection.matched:
                continue
            if best is None or detection.confidence > best[1].confidence:
                best = (parser, detection)
        if best is None:
            return None, None
        return best
