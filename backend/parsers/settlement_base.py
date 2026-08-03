"""Settlement parser contract — Pandas stays inside implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from backend.parsers.base import ParserDetection
from backend.parsers.canonical import CanonicalDataset, ValidationIssue


@dataclass
class SettlementParseResult:
    """Outcome of parsing one settlement file (no Pandas)."""

    dataset: CanonicalDataset
    detection: ParserDetection
    issues: list[ValidationIssue] = field(default_factory=list)
    rows_read: int = 0
    null_order_ids: int = 0
    null_amounts: int = 0
    negative_amounts: int = 0
    future_dates: int = 0
    duplicate_order_ids: int = 0
    invalid_dates: int = 0
    is_valid: bool = True


class SettlementParser(ABC):
    """
    Parser for aggregator settlement reports (Swiggy, Zomato, future Blinkit…).

    Implementations may use Pandas internally but must only return
    :class:`CanonicalDataset` / :class:`SettlementParseResult`.
    """

    @property
    @abstractmethod
    def parser_id(self) -> str: ...

    @property
    @abstractmethod
    def platform(self) -> str: ...

    @property
    @abstractmethod
    def source(self) -> str: ...

    @property
    def currency(self) -> str:
        return "INR"

    @abstractmethod
    def detect(self, filename: str, content: bytes) -> ParserDetection:
        """Return whether this parser can handle the upload (load internally)."""

    @abstractmethod
    def parse(self, filename: str, content: bytes) -> SettlementParseResult:
        """Parse upload into a canonical settlement dataset."""
