"""
Classification predicates for the Business Rules Engine.

Pure functions / small classes — no reconciliation math, no file I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from backend.business_rules.result import ReconciliationStatus
from backend.business_rules.rules import BusinessRulesConfig, PlatformRuleConfig


class SettlementCoverage(Protocol):
    """Minimal settlement metadata surface (DatasetMetadata-compatible)."""

    start_date: str | None
    end_date: str | None


@dataclass(frozen=True)
class OrderFacts:
    """External facts supplied alongside a reconciliation row."""

    order_id: str
    platform: str | None = None
    order_date: date | None = None
    cancelled: bool = False


def parse_iso_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def is_zero_difference(
    difference: Decimal | None,
    *,
    tolerance: Decimal,
) -> bool:
    if difference is None:
        return False
    return abs(difference) <= tolerance


def settlement_period_uploaded(
    order_date: date | None,
    coverage: SettlementCoverage | None,
    platform_rule: PlatformRuleConfig,
    *,
    as_of: date,
) -> bool:
    """
    Return True when the settlement period for ``order_date`` is considered uploaded.

    Logic:
    1. If the order is still inside the platform delay window
       (``as_of < order_date + delay_days``) → period not yet due → False.
    2. If settlement coverage dates exist and ``order_date`` falls within
       ``[start_date, end_date]`` → True (period present in upload).
    3. If coverage exists and ``order_date`` is on/before ``end_date`` and
       the delay window has elapsed → True (period should be in this upload).
    4. Otherwise → False.
    """
    if order_date is None:
        # Without an order date, treat period as uploaded only if any settlement exists.
        return bool(
            coverage
            and (getattr(coverage, "start_date", None) or getattr(coverage, "end_date", None))
        )

    due_date = order_date + timedelta(days=platform_rule.delay_days)
    if as_of < due_date:
        return False

    if coverage is None:
        return False

    start = parse_iso_date(getattr(coverage, "start_date", None))
    end = parse_iso_date(getattr(coverage, "end_date", None))

    if start is None and end is None:
        return False

    if start is not None and end is not None:
        return start <= order_date <= end

    if end is not None:
        return order_date <= end

    assert start is not None
    return order_date >= start


class StatusClassifier:
    """
    Classify a single reconciliation outcome into a :class:`ReconciliationStatus`.

    Does not recompute amounts — reads difference / matched flags only.
    """

    def __init__(self, config: BusinessRulesConfig) -> None:
        self._config = config

    def classify_matched(
        self,
        *,
        cancelled: bool,
        difference: Decimal | None,
        platform: str | None,
        financial_status: str | None = None,
    ) -> ReconciliationStatus:
        if cancelled:
            return ReconciliationStatus.CANCELLED
        # Sprint 6A — prefer platform-engine financial status
        if financial_status == "FINANCIALLY_RECONCILED":
            return ReconciliationStatus.FINANCIALLY_RECONCILED
        if financial_status == "FINANCIAL_DISCREPANCY":
            return ReconciliationStatus.FINANCIAL_DISCREPANCY
        if financial_status == "INCOMPLETE_DATA":
            return ReconciliationStatus.MANUAL_REVIEW
        rule = self._config.for_platform(platform)
        if difference is None:
            return ReconciliationStatus.MANUAL_REVIEW
        if is_zero_difference(difference, tolerance=rule.zero_difference_tolerance):
            return ReconciliationStatus.FINANCIALLY_RECONCILED
        return ReconciliationStatus.FINANCIAL_DISCREPANCY

    def classify_unmatched_pos(
        self,
        *,
        cancelled: bool,
        platform: str | None,
        order_date: date | None,
        coverage: SettlementCoverage | None,
        as_of: date,
        is_duplicate_settlement: bool = False,
    ) -> ReconciliationStatus:
        if cancelled:
            return ReconciliationStatus.CANCELLED
        if is_duplicate_settlement:
            return ReconciliationStatus.DUPLICATE_SETTLEMENT
        rule = self._config.for_platform(platform)
        if settlement_period_uploaded(order_date, coverage, rule, as_of=as_of):
            return ReconciliationStatus.NOT_RECONCILED
        return ReconciliationStatus.PENDING

    def classify_unmatched_settlement(
        self,
        *,
        is_duplicate: bool,
    ) -> ReconciliationStatus:
        if is_duplicate:
            return ReconciliationStatus.DUPLICATE_SETTLEMENT
        return ReconciliationStatus.MANUAL_REVIEW
