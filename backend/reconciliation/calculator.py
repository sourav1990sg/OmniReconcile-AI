"""
Amount calculator for Reconciliation Engine V2.

difference = settled − expected  (Decimal arithmetic only)
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class AmountCalculator:
    """Compute expected, settled, and difference using :class:`Decimal`."""

    def expected_amount(self, pos_expected: Any) -> Decimal:
        """POS Expected Amount as Decimal."""
        return self.to_decimal(pos_expected)

    def settled_amount(self, settlement_amount: Any) -> Decimal:
        """Settlement Amount as Decimal."""
        return self.to_decimal(settlement_amount)

    def difference(self, *, settled: Decimal, expected: Decimal) -> Decimal:
        """Settled − Expected."""
        return settled - expected

    def compute(
        self,
        pos_expected: Any,
        settlement_amount: Any,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Return ``(expected, settled, difference)``.

        difference = settled − expected
        """
        expected = self.expected_amount(pos_expected)
        settled = self.settled_amount(settlement_amount)
        diff = self.difference(settled=settled, expected=expected)
        quant = Decimal("0.01")
        return expected.quantize(quant), settled.quantize(quant), diff.quantize(quant)

    @staticmethod
    def to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal("0")
        if isinstance(value, bool):
            raise TypeError("Boolean is not a valid monetary value")
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))
        text = str(value).strip().replace(",", "")
        if not text:
            return Decimal("0")
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Cannot convert {value!r} to Decimal") from exc
