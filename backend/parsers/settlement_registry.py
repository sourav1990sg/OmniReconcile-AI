"""Registry for settlement parsers (open for Blinkit, Zepto, Magicpin, …)."""

from __future__ import annotations

from typing import Sequence

from backend.parsers.base import ParserDetection
from backend.parsers.settlement_base import SettlementParser


class SettlementParserRegistry:
    """
    Holds settlement parsers. New platforms register without changing callers.

    Detection picks the highest-confidence match among registered parsers.
    """

    def __init__(self, parsers: Sequence[SettlementParser] | None = None) -> None:
        if parsers is not None:
            self._parsers = list(parsers)
        else:
            # Lazy default registration to avoid circular imports at module load
            from backend.parsers.swiggy import SwiggySettlementParser
            from backend.parsers.zomato import ZomatoSettlementParser

            self._parsers = [SwiggySettlementParser(), ZomatoSettlementParser()]

    def register(self, parser: SettlementParser) -> None:
        """Register an additional settlement parser (OCP)."""
        self._parsers.append(parser)

    def all_parsers(self) -> tuple[SettlementParser, ...]:
        return tuple(self._parsers)

    def get(self, parser_id: str) -> SettlementParser | None:
        for parser in self._parsers:
            if parser.parser_id == parser_id:
                return parser
        return None

    def detect(
        self,
        filename: str,
        content: bytes,
    ) -> tuple[SettlementParser | None, ParserDetection | None]:
        best: tuple[SettlementParser, ParserDetection] | None = None
        for parser in self._parsers:
            detection = parser.detect(filename, content)
            if not detection.matched:
                continue
            if best is None or detection.confidence > best[1].confidence:
                best = (parser, detection)
        if best is None:
            return None, None
        return best
