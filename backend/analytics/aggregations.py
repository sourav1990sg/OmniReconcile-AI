"""
Shared aggregation primitives — every KPI is computed once here.

Platform / outlet / financial / trends modules only reshape these buckets.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping


def money(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(Decimal(str(value)).quantize(Decimal("0.01")))
    except Exception:  # noqa: BLE001
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return 0.0


def pct(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def normalize_platform(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "swiggy" in text:
        return "Swiggy"
    if "zomato" in text:
        return "Zomato"
    return "Unknown"


def normalize_outlet(value: Any) -> str:
    """Canonical outlet label — never returns the literal 'Unknown'."""
    from backend.data_quality import canonical_outlet_name

    return canonical_outlet_name(value)


def is_matched(row: Mapping[str, Any]) -> bool:
    return bool(row.get("Matched"))


def verification_level(row: Mapping[str, Any]) -> str:
    return str(row.get("Verification Level") or "").upper()


def business_status(row: Mapping[str, Any]) -> str:
    return str(row.get("Status") or "").upper()


def financial_status(row: Mapping[str, Any]) -> str:
    return str(row.get("Financial Status") or row.get("Status") or "").upper()


def is_payment_match(row: Mapping[str, Any]) -> bool:
    level = verification_level(row)
    if level in {"SETTLEMENT_VERIFIED", "AGREEMENT_VERIFIED"}:
        return True
    display = str(row.get("Display Status") or "")
    return display in {"Payment Match", "Verified by Agreement"}


def is_agreement_verified(row: Mapping[str, Any]) -> bool:
    return verification_level(row) == "AGREEMENT_VERIFIED"


def is_agreement_violation(row: Mapping[str, Any]) -> bool:
    return verification_level(row) == "AGREEMENT_VIOLATION"


def recoverable_for_row(row: Mapping[str, Any]) -> float:
    """Unexplained underpayment only (Sprint 6A definition)."""
    status = business_status(row)
    # Business-rule status gates recoverable — cancelled / unmatched never count
    if status != "FINANCIAL_DISCREPANCY":
        return 0.0
    calc = money(row.get("Calculated Payout", row.get("Expected Amount")))
    act = money(row.get("Actual Payout", row.get("Settled Amount")))
    short = calc - act
    return round(short, 2) if short > 0 else 0.0


def breakdown(row: Mapping[str, Any]) -> dict[str, Any]:
    bd = row.get("Financial Breakdown")
    return bd if isinstance(bd, dict) else {}


def components(row: Mapping[str, Any]) -> dict[str, Any]:
    bd = breakdown(row)
    comps = bd.get("components")
    return comps if isinstance(comps, dict) else {}


@dataclass
class MetricBucket:
    """Single accumulation cell — used for platform and outlet dimensions."""

    order_count: int = 0
    matched_count: int = 0
    sales: float = 0.0
    gross_order_value: float = 0.0
    platform_payout: float = 0.0
    commission: float = 0.0
    payment_fees: float = 0.0
    gst: float = 0.0
    government_charges: float = 0.0
    tcs: float = 0.0
    tds: float = 0.0
    restaurant_discount: float = 0.0
    platform_discount: float = 0.0
    promo_recovery: float = 0.0
    customer_compensation: float = 0.0
    other_deductions: float = 0.0
    net_deductions: float = 0.0
    recoverable: float = 0.0
    payment_match: int = 0
    agreement_verified: int = 0
    agreement_violations: int = 0
    cancelled: int = 0
    pending: int = 0
    not_reconciled: int = 0
    financially_reconciled: int = 0
    financial_discrepancy: int = 0

    def add_row(self, row: Mapping[str, Any], *, count_order: bool = True) -> None:
        if count_order:
            self.order_count += 1
        status = business_status(row)
        fin = financial_status(row)
        if status == "CANCELLED":
            self.cancelled += 1
        if status == "PENDING":
            self.pending += 1
        if status == "NOT_RECONCILED":
            self.not_reconciled += 1
        if not is_matched(row):
            return

        self.matched_count += 1
        self.sales += money(row.get("POS Sale"))
        self.gross_order_value += money(row.get("Gross Order Value"))
        self.platform_payout += money(row.get("Actual Payout", row.get("Settled Amount")))
        self.recoverable += recoverable_for_row(row)

        bd = breakdown(row)
        comps = components(row)
        self.commission += money(bd.get("commission"))
        self.payment_fees += money(bd.get("payment_fee"))
        self.gst += money(bd.get("gst"))
        self.government_charges += money(comps.get("government_charges") or bd.get("government_charges"))
        self.tcs += money(bd.get("tcs"))
        self.tds += money(bd.get("tds"))
        self.promo_recovery += money(bd.get("promo_recovery"))
        self.customer_compensation += money(bd.get("penalties") or comps.get("customer_compensation"))
        self.other_deductions += money(bd.get("other_deductions"))
        self.net_deductions += money(row.get("Total Deductions") or bd.get("total_deductions"))
        self.restaurant_discount += money(comps.get("merchant_discount") or comps.get("restaurant_discount"))
        self.platform_discount += money(
            comps.get("discount_on_platform_fee") or comps.get("platform_discount")
        )

        if is_payment_match(row):
            self.payment_match += 1
        if is_agreement_verified(row):
            self.agreement_verified += 1
        if is_agreement_violation(row):
            self.agreement_violations += 1
        if fin in {"FINANCIALLY_RECONCILED", "RECONCILED"} or status in {
            "FINANCIALLY_RECONCILED",
            "RECONCILED",
        }:
            if status not in {"CANCELLED"}:
                self.financially_reconciled += 1
        if status == "FINANCIAL_DISCREPANCY":
            self.financial_discrepancy += 1

    @property
    def aov(self) -> float:
        return pct(self.sales, self.matched_count) / 100.0 if self.matched_count else 0.0

    def average_order_value(self) -> float:
        if not self.matched_count:
            return 0.0
        return round(self.sales / self.matched_count, 2)


@dataclass
class AggregationIndex:
    """
    One-pass index over reconciliation rows.

    All section builders read from this — no duplicated loops for money totals.
    """

    global_bucket: MetricBucket = field(default_factory=MetricBucket)
    by_platform: dict[str, MetricBucket] = field(default_factory=dict)
    by_outlet: dict[str, MetricBucket] = field(default_factory=dict)
    outlet_platform_orders: dict[str, dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    by_day: dict[str, MetricBucket] = field(default_factory=dict)
    all_rows: list[Mapping[str, Any]] = field(default_factory=list)
    matched_rows: list[Mapping[str, Any]] = field(default_factory=list)

    @classmethod
    def build(cls, rows: list[Mapping[str, Any]]) -> "AggregationIndex":
        index = cls()
        index.all_rows = list(rows)
        for row in rows:
            platform = normalize_platform(row.get("Platform"))
            outlet = normalize_outlet(row.get("Outlet"))
            day = str(row.get("Date") or "")[:10] or "unknown"

            index.global_bucket.add_row(row, count_order=True)

            if platform not in index.by_platform:
                index.by_platform[platform] = MetricBucket()
            index.by_platform[platform].add_row(row, count_order=True)

            if outlet not in index.by_outlet:
                index.by_outlet[outlet] = MetricBucket()
            index.by_outlet[outlet].add_row(row, count_order=True)

            index.outlet_platform_orders[outlet][platform] += 1

            if day not in index.by_day:
                index.by_day[day] = MetricBucket()
            index.by_day[day].add_row(row, count_order=True)

            if is_matched(row):
                index.matched_rows.append(row)
        return index
