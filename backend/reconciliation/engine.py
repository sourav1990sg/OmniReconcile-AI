"""
Reconciliation Engine V2 + Sprint 6A Platform Financial Reconciliation.

Flow:
  POS + Settlement → Match Order ID → Platform Engine → Financial Breakdown
  → Calculated Payout vs Actual Settlement → Financial Difference
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Protocol, Sequence, runtime_checkable

from backend.ingestion.logging_utils import log_with_context
from backend.platform_engines.factory import PlatformEngineFactory
from backend.platform_engines.models import FinancialStatus
from backend.platform_engines.settlement_rows import SettlementFinancialIndex
from backend.reconciliation.calculator import AmountCalculator
from backend.reconciliation.matcher import (
    MatchedPair,
    MatchResult,
    OrderMatcher,
    PosOrderLike,
    SettlementOrderLike,
)
from backend.reconciliation.result import (
    DifferenceSummary,
    ReconciliationReport,
    ReconciliationResult,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class DatasetLike(Protocol):
    """Accept POS or settlement CanonicalDataset without importing Pandas."""

    def __iter__(self) -> Any: ...


class ReconciliationEngine:
    """
    Match on Aggregator Order ID, then apply platform financial engines.

    When a SettlementFinancialIndex is provided, matched differences are
    calculated_payout vs actual settlement payout (not POS My Amount).
    """

    def __init__(
        self,
        matcher: OrderMatcher | None = None,
        calculator: AmountCalculator | None = None,
        engine_factory: PlatformEngineFactory | None = None,
        *,
        financial_tolerance: Decimal = Decimal("0.01"),
    ) -> None:
        self._matcher = matcher or OrderMatcher()
        self._calculator = calculator or AmountCalculator()
        self._factory = engine_factory or PlatformEngineFactory()
        self._tolerance = financial_tolerance

    def reconcile(
        self,
        pos_dataset: DatasetLike | Sequence[PosOrderLike],
        settlement_dataset: DatasetLike | Sequence[SettlementOrderLike],
        *,
        financial_index: SettlementFinancialIndex | None = None,
    ) -> ReconciliationReport:
        pos_orders = self._extract_orders(pos_dataset)
        settlement_orders = self._extract_orders(settlement_dataset)

        match_result = self._matcher.match(pos_orders, settlement_orders)
        report = self._build_report(match_result, financial_index=financial_index)

        log_with_context(
            logger,
            logging.INFO,
            "Reconciliation complete",
            matched=len(report.matched),
            unmatched_pos=len(report.unmatched_pos),
            unmatched_settlement=len(report.unmatched_settlement),
            total_difference=str(report.summary.total_difference) if report.summary else None,
            financial_mode=bool(financial_index),
        )
        return report

    def _build_report(
        self,
        match_result: MatchResult,
        *,
        financial_index: SettlementFinancialIndex | None,
    ) -> ReconciliationReport:
        matched_rows = [
            self._row_from_pair(pair, financial_index=financial_index)
            for pair in match_result.matched
        ]
        unmatched_pos_rows = [
            self._row_unmatched_pos(order) for order in match_result.unmatched_pos
        ]
        unmatched_settle_rows = [
            self._row_unmatched_settlement(order)
            for order in match_result.unmatched_settlement
        ]
        summary = self._summarize(
            matched_rows,
            unmatched_pos_count=len(unmatched_pos_rows),
            unmatched_settlement_count=len(unmatched_settle_rows),
        )
        return ReconciliationReport(
            matched=matched_rows,
            unmatched_pos=unmatched_pos_rows,
            unmatched_settlement=unmatched_settle_rows,
            summary=summary,
        )

    def _row_from_pair(
        self,
        pair: MatchedPair,
        *,
        financial_index: SettlementFinancialIndex | None,
    ) -> ReconciliationResult:
        platform = pair.settlement.platform or pair.pos.platform
        pos_sale = self._calculator.expected_amount(pair.pos.expected_amount)
        actual = self._calculator.settled_amount(pair.settlement.settled_amount)
        order_id = str(pair.pos.aggregator_order_id)

        fin_entry = financial_index.get(order_id) if financial_index else None
        engine = self._factory.get(
            (fin_entry or {}).get("platform") if fin_entry else platform
        )

        if engine and fin_entry and fin_entry.get("row"):
            breakdown = engine.compute(
                order_id=order_id,
                settlement_row=fin_entry["row"],
                actual_payout=actual,
                pos_sale=pos_sale,
                tolerance=self._tolerance,
            )
            return ReconciliationResult(
                order_id=order_id,
                platform=platform,
                expected_amount=breakdown.calculated_payout,
                settled_amount=breakdown.actual_payout,
                difference=breakdown.financial_difference,
                matched=True,
                remarks=breakdown.explanation,
                source_pos_document=pair.pos.source_file,
                source_settlement_document=pair.settlement.source_file,
                pos_sale=breakdown.gross_sale,
                gross_order_value=breakdown.gross_order_value,
                total_deductions=breakdown.total_deductions,
                calculated_payout=breakdown.calculated_payout,
                actual_payout=breakdown.actual_payout,
                financial_difference=breakdown.financial_difference,
                financial_status=breakdown.financial_status.value,
                formula_used=breakdown.formula_used,
                explanation=breakdown.explanation,
                deduction_summary=dict(breakdown.deduction_summary),
                financial_breakdown=breakdown.to_dict(),
            )

        # Fallback: legacy POS vs settlement comparison when no financial row
        expected, settled, diff = self._calculator.compute(
            pair.pos.expected_amount,
            pair.settlement.settled_amount,
        )
        return ReconciliationResult(
            order_id=order_id,
            platform=platform,
            expected_amount=expected,
            settled_amount=settled,
            difference=diff,
            matched=True,
            remarks="Matched (legacy amount compare — financial row unavailable)",
            source_pos_document=pair.pos.source_file,
            source_settlement_document=pair.settlement.source_file,
            pos_sale=pos_sale,
            calculated_payout=expected,
            actual_payout=settled,
            financial_difference=diff,
            financial_status=(
                FinancialStatus.FINANCIALLY_RECONCILED.value
                if abs(diff) <= self._tolerance
                else FinancialStatus.FINANCIAL_DISCREPANCY.value
            ),
            formula_used="legacy: settlement_payout − pos_my_amount",
            explanation="Financial settlement components unavailable; used legacy comparison.",
            deduction_summary={},
            financial_breakdown=None,
        )

    def _row_unmatched_pos(self, order: PosOrderLike) -> ReconciliationResult:
        expected = self._calculator.expected_amount(order.expected_amount)
        return ReconciliationResult(
            order_id=str(order.aggregator_order_id),
            platform=order.platform,
            expected_amount=expected,
            settled_amount=None,
            difference=None,
            matched=False,
            remarks="Unmatched POS",
            source_pos_document=order.source_file,
            source_settlement_document=None,
            pos_sale=expected,
        )

    def _row_unmatched_settlement(self, order: SettlementOrderLike) -> ReconciliationResult:
        settled = self._calculator.settled_amount(order.settled_amount)
        return ReconciliationResult(
            order_id=str(order.aggregator_order_id),
            platform=order.platform,
            expected_amount=None,
            settled_amount=settled,
            difference=None,
            matched=False,
            remarks="Unmatched Settlement",
            source_pos_document=None,
            source_settlement_document=order.source_file,
            actual_payout=settled,
        )

    def _summarize(
        self,
        matched: Sequence[ReconciliationResult],
        *,
        unmatched_pos_count: int,
        unmatched_settlement_count: int,
    ) -> DifferenceSummary:
        total_expected = Decimal("0")
        total_settled = Decimal("0")
        total_difference = Decimal("0")
        positive = Decimal("0")
        negative = Decimal("0")

        for row in matched:
            assert row.expected_amount is not None
            assert row.settled_amount is not None
            assert row.difference is not None
            total_expected += row.expected_amount
            total_settled += row.settled_amount
            total_difference += row.difference
            if row.difference > 0:
                positive += row.difference
            elif row.difference < 0:
                negative += row.difference

        quant = Decimal("0.01")
        return DifferenceSummary(
            matched_count=len(matched),
            unmatched_pos_count=unmatched_pos_count,
            unmatched_settlement_count=unmatched_settlement_count,
            total_expected=total_expected.quantize(quant),
            total_settled=total_settled.quantize(quant),
            total_difference=total_difference.quantize(quant),
            positive_difference_sum=positive.quantize(quant),
            negative_difference_sum=negative.quantize(quant),
        )

    @staticmethod
    def _extract_orders(dataset: DatasetLike | Sequence[Any]) -> list[Any]:
        if dataset is None:
            return []
        orders_attr = getattr(dataset, "orders", None)
        if callable(orders_attr):
            return list(orders_attr())
        if isinstance(orders_attr, (tuple, list)):
            return list(orders_attr)
        if isinstance(dataset, (list, tuple)):
            return list(dataset)
        return list(dataset)
