"""Abstract parser contract for source-system report parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence

import pandas as pd


@dataclass(frozen=True)
class ParserDetection:
    """Result of asking a parser whether it can handle a raw table."""

    matched: bool
    platform: str
    source: str
    column_map: dict[str, str]
    confidence: float
    reasons: tuple[str, ...] = ()
    currency: str = "INR"


@dataclass
class ParseResult:
    """Canonical rows produced by a parser for one file."""

    dataframe: pd.DataFrame
    null_order_ids: int = 0
    null_amounts: int = 0
    platform: str = ""
    source: str = ""
    currency: str = "INR"
    extras: dict[str, int] = field(default_factory=dict)


class SourceParser(ABC):
    """
    Parser for a single upstream source (Petpooja, future Swiggy POS, etc.).

    Ingestion loads/detects/validates/routes; parsers own aliases and mapping.
    """

    @property
    @abstractmethod
    def parser_id(self) -> str:
        """Stable identifier, e.g. ``petpooja``."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform key stored on DatasetMetadata."""

    @property
    @abstractmethod
    def source(self) -> str:
        """Human-readable source label."""

    @property
    def currency(self) -> str:
        return "INR"

    @abstractmethod
    def detect(self, df: pd.DataFrame, filename: str | None = None) -> ParserDetection:
        """Return whether this parser can handle the raw DataFrame."""

    @abstractmethod
    def parse(
        self,
        df: pd.DataFrame,
        column_map: dict[str, str],
        *,
        source_file: str,
    ) -> ParseResult:
        """Map a raw file onto the canonical POS schema."""

    def required_roles(self) -> Sequence[str]:
        """Semantic roles that must be present for a successful detection."""
        return ("order_id", "amount", "date", "outlet")
