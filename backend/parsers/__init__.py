"""Source-system parsers for OmniReconcile AI."""

from backend.parsers.base import ParseResult, ParserDetection, SourceParser
from backend.parsers.canonical import CanonicalDataset, CanonicalOrder, DatasetMetadata
from backend.parsers.petpooja import PetpoojaParser
from backend.parsers.registry import ParserRegistry
from backend.parsers.settlement_base import SettlementParseResult, SettlementParser
from backend.parsers.settlement_registry import SettlementParserRegistry
from backend.parsers.swiggy import SwiggySettlementParser
from backend.parsers.zomato import ZomatoSettlementParser

__all__ = [
    "CanonicalDataset",
    "CanonicalOrder",
    "DatasetMetadata",
    "ParseResult",
    "ParserDetection",
    "ParserRegistry",
    "PetpoojaParser",
    "SettlementParseResult",
    "SettlementParser",
    "SettlementParserRegistry",
    "SourceParser",
    "SwiggySettlementParser",
    "ZomatoSettlementParser",
]
