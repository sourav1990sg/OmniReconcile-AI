"""Abstract platform financial engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Mapping

from backend.platform_engines.models import FinancialBreakdown, FinancialStatus


class PlatformFinancialEngine(ABC):
    """Compute expected settlement payout from platform settlement components."""

    @property
    @abstractmethod
    def platform(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def compute(
        self,
        *,
        order_id: str,
        settlement_row: Mapping[str, Any],
        actual_payout: Decimal | None,
        pos_sale: Decimal | None = None,
        tolerance: Decimal = Decimal("0.01"),
    ) -> FinancialBreakdown:
        raise NotImplementedError

    def _finalize(
        self,
        breakdown: FinancialBreakdown,
        *,
        tolerance: Decimal,
    ) -> FinancialBreakdown:
        diff = (breakdown.actual_payout - breakdown.calculated_payout).quantize(Decimal("0.01"))
        breakdown.financial_difference = diff
        if abs(diff) <= tolerance:
            breakdown.financial_status = FinancialStatus.FINANCIALLY_RECONCILED
            breakdown.explanation = (
                breakdown.explanation
                or "Calculated payout matches actual settlement payout within tolerance."
            )
        else:
            breakdown.financial_status = FinancialStatus.FINANCIAL_DISCREPANCY
            breakdown.explanation = (
                breakdown.explanation
                or (
                    f"Unexplained payout gap of ₹{diff}: "
                    f"calculated ₹{breakdown.calculated_payout} vs actual ₹{breakdown.actual_payout}."
                )
            )
        return breakdown
