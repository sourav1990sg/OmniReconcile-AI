"""Financial breakdown models for platform reconciliation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class FinancialStatus(str, Enum):
    """Platform-engine financial classification (pre–business-rules)."""

    FINANCIALLY_RECONCILED = "FINANCIALLY_RECONCILED"
    FINANCIAL_DISCREPANCY = "FINANCIAL_DISCREPANCY"
    INCOMPLETE_DATA = "INCOMPLETE_DATA"


def _q(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


@dataclass
class FinancialBreakdown:
    """
    Common financial explanation for one matched order.

    ``financial_difference`` = actual_payout − calculated_payout.
    """

    platform: str
    order_id: str
    formula_used: str
    gross_sale: Decimal = Decimal("0.00")  # POS My Amount (context only)
    gross_order_value: Decimal = Decimal("0.00")
    commission: Decimal = Decimal("0.00")
    payment_fee: Decimal = Decimal("0.00")
    delivery_fee: Decimal = Decimal("0.00")
    packaging_adjustment: Decimal = Decimal("0.00")
    gst: Decimal = Decimal("0.00")
    tcs: Decimal = Decimal("0.00")
    tds: Decimal = Decimal("0.00")
    ads: Decimal = Decimal("0.00")
    promo_recovery: Decimal = Decimal("0.00")
    brand_pack: Decimal = Decimal("0.00")
    loyalty: Decimal = Decimal("0.00")
    penalties: Decimal = Decimal("0.00")
    other_deductions: Decimal = Decimal("0.00")
    other_additions: Decimal = Decimal("0.00")
    total_deductions: Decimal = Decimal("0.00")
    calculated_payout: Decimal = Decimal("0.00")
    actual_payout: Decimal = Decimal("0.00")
    financial_difference: Decimal = Decimal("0.00")
    financial_status: FinancialStatus = FinancialStatus.INCOMPLETE_DATA
    explanation: str = ""
    deduction_summary: dict[str, float] = field(default_factory=dict)
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["financial_status"] = self.financial_status.value
        for key, value in list(payload.items()):
            if isinstance(value, Decimal):
                payload[key] = float(value)
        return payload

    @staticmethod
    def quantize(value: Any) -> Decimal:
        return _q(value if not isinstance(value, Decimal) else value)
