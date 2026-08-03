"""
Reconciliation result types (Sprint / Engine V2 + Sprint 6A financial fields).

No file I/O. No Pandas. Decimal-only money fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Sequence


@dataclass(frozen=True)
class ReconciliationResult:
    """One reconciliation row for a single Aggregator Order ID pairing."""

    order_id: str
    platform: str | None
    expected_amount: Decimal | None  # Sprint 6A: calculated payout (legacy field name kept)
    settled_amount: Decimal | None  # Sprint 6A: actual settlement payout
    difference: Decimal | None  # actual − calculated
    matched: bool
    remarks: str
    source_pos_document: str | None
    source_settlement_document: str | None
    # Sprint 6A financial reconciliation
    pos_sale: Decimal | None = None
    gross_order_value: Decimal | None = None
    total_deductions: Decimal | None = None
    calculated_payout: Decimal | None = None
    actual_payout: Decimal | None = None
    financial_difference: Decimal | None = None
    financial_status: str | None = None
    formula_used: str | None = None
    explanation: str | None = None
    deduction_summary: dict[str, float] | None = None
    financial_breakdown: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "platform": self.platform,
            "expected_amount": str(self.expected_amount) if self.expected_amount is not None else None,
            "settled_amount": str(self.settled_amount) if self.settled_amount is not None else None,
            "difference": str(self.difference) if self.difference is not None else None,
            "matched": self.matched,
            "remarks": self.remarks,
            "source_pos_document": self.source_pos_document,
            "source_settlement_document": self.source_settlement_document,
            "pos_sale": str(self.pos_sale) if self.pos_sale is not None else None,
            "gross_order_value": str(self.gross_order_value) if self.gross_order_value is not None else None,
            "total_deductions": str(self.total_deductions) if self.total_deductions is not None else None,
            "calculated_payout": str(self.calculated_payout) if self.calculated_payout is not None else None,
            "actual_payout": str(self.actual_payout) if self.actual_payout is not None else None,
            "financial_difference": str(self.financial_difference)
            if self.financial_difference is not None
            else None,
            "financial_status": self.financial_status,
            "formula_used": self.formula_used,
            "explanation": self.explanation,
            "deduction_summary": self.deduction_summary,
            "financial_breakdown": self.financial_breakdown,
        }


@dataclass(frozen=True)
class DifferenceSummary:
    """Aggregate difference statistics over matched rows only."""

    matched_count: int
    unmatched_pos_count: int
    unmatched_settlement_count: int
    total_expected: Decimal
    total_settled: Decimal
    total_difference: Decimal
    positive_difference_sum: Decimal
    negative_difference_sum: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_count": self.matched_count,
            "unmatched_pos_count": self.unmatched_pos_count,
            "unmatched_settlement_count": self.unmatched_settlement_count,
            "total_expected": str(self.total_expected),
            "total_settled": str(self.total_settled),
            "total_difference": str(self.total_difference),
            "positive_difference_sum": str(self.positive_difference_sum),
            "negative_difference_sum": str(self.negative_difference_sum),
        }


@dataclass
class ReconciliationReport:
    """Full engine output: matched + unmatched buckets and difference summary."""

    matched: list[ReconciliationResult] = field(default_factory=list)
    unmatched_pos: list[ReconciliationResult] = field(default_factory=list)
    unmatched_settlement: list[ReconciliationResult] = field(default_factory=list)
    summary: DifferenceSummary | None = None

    @property
    def all_results(self) -> list[ReconciliationResult]:
        return [*self.matched, *self.unmatched_pos, *self.unmatched_settlement]

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_orders": len(self.matched),
            "unmatched_pos": len(self.unmatched_pos),
            "unmatched_settlement": len(self.unmatched_settlement),
            "difference_summary": self.summary.to_dict() if self.summary else None,
            "matched": [r.to_dict() for r in self.matched],
            "unmatched_pos_rows": [r.to_dict() for r in self.unmatched_pos],
            "unmatched_settlement_rows": [r.to_dict() for r in self.unmatched_settlement],
        }
