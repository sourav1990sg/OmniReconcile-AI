"""AnalyticsReport schema and section models (Sprint 7A)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _round2(value: float) -> float:
    return round(float(value), 2)


@dataclass
class ExecutiveSummary:
    total_pos_orders: int = 0
    cancelled_orders: int = 0
    eligible_orders: int = 0
    matched_orders: int = 0
    payment_match_orders: int = 0
    agreement_verified_orders: int = 0
    agreement_violations: int = 0
    pending_orders: int = 0
    not_reconciled_orders: int = 0
    settlement_coverage_pct: float = 0.0
    recoverable_amount: float = 0.0
    total_online_sales: float = 0.0  # POS sale on matched
    gross_order_value: float = 0.0
    platform_payout: float = 0.0
    total_settlement_orders: int = 0
    financial_discrepancy_orders: int = 0
    financially_reconciled_orders: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {k: (_round2(v) if isinstance(v, float) else v) for k, v in asdict(self).items()}


@dataclass
class PlatformSummary:
    platform: str
    order_count: int = 0
    sales: float = 0.0
    gross_order_value: float = 0.0
    platform_payout: float = 0.0
    average_order_value: float = 0.0
    commission: float = 0.0
    government_charges: float = 0.0
    tds: float = 0.0
    tcs: float = 0.0
    gst: float = 0.0
    restaurant_discount: float = 0.0
    platform_discount: float = 0.0
    promo_recovery: float = 0.0
    customer_compensation: float = 0.0
    other_deductions: float = 0.0
    net_deductions: float = 0.0
    recoverable_amount: float = 0.0
    settlement_coverage_pct: float = 0.0
    payment_match_pct: float = 0.0
    agreement_verification_pct: float = 0.0
    payment_match_orders: int = 0
    agreement_verified_orders: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {k: (_round2(v) if isinstance(v, float) else v) for k, v in asdict(self).items()}


@dataclass
class OutletSummary:
    outlet: str
    swiggy_orders: int = 0
    zomato_orders: int = 0
    total_orders: int = 0
    sales: float = 0.0
    gross_order_value: float = 0.0
    platform_payout: float = 0.0
    average_order_value: float = 0.0
    commission: float = 0.0
    recoverable_amount: float = 0.0
    payment_match_pct: float = 0.0
    agreement_verified_pct: float = 0.0
    cancelled: int = 0
    pending: int = 0
    platform_wise_orders: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for k, v in list(payload.items()):
            if isinstance(v, float):
                payload[k] = _round2(v)
        return payload


@dataclass
class TopPerformers:
    highest_online_sales_outlet: str | None = None
    highest_orders_outlet: str | None = None
    highest_average_order_value: str | None = None
    highest_recoverable_amount: str | None = None
    lowest_performing_outlet: str | None = None
    most_cancelled_outlet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FinancialSummary:
    total_pos_sales: float = 0.0
    gross_order_value: float = 0.0
    total_commission: float = 0.0
    total_payment_fees: float = 0.0
    total_gst: float = 0.0
    total_government_charges: float = 0.0
    total_tcs: float = 0.0
    total_tds: float = 0.0
    total_platform_deductions: float = 0.0
    total_promo_recovery: float = 0.0
    total_customer_compensation: float = 0.0
    net_platform_payout: float = 0.0
    recoverable: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {k: _round2(v) for k, v in asdict(self).items()}


@dataclass
class PlatformComparison:
    swiggy_order_share_pct: float = 0.0
    zomato_order_share_pct: float = 0.0
    swiggy_revenue_share_pct: float = 0.0
    zomato_revenue_share_pct: float = 0.0
    swiggy_payout_share_pct: float = 0.0
    zomato_payout_share_pct: float = 0.0
    swiggy_commission_pct: float = 0.0
    zomato_commission_pct: float = 0.0
    swiggy_aov: float = 0.0
    zomato_aov: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {k: _round2(v) for k, v in asdict(self).items()}


@dataclass
class TrendMetrics:
    orders_by_day: list[dict[str, Any]] = field(default_factory=list)
    sales_by_day: list[dict[str, Any]] = field(default_factory=list)
    payout_by_day: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KpiCard:
    id: str
    label: str
    value: str
    caption: str
    tone: str = "neutral"  # neutral | warning | success

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalyticsReport:
    """
    Single source of truth for all business KPIs.

    Dashboard / PDF / Excel / AI must consume this object — never recompute.
    """

    executive_summary: ExecutiveSummary = field(default_factory=ExecutiveSummary)
    platform_summary: list[PlatformSummary] = field(default_factory=list)
    outlet_summary: list[OutletSummary] = field(default_factory=list)
    top_performers: TopPerformers = field(default_factory=TopPerformers)
    financial_summary: FinancialSummary = field(default_factory=FinancialSummary)
    platform_comparison: PlatformComparison = field(default_factory=PlatformComparison)
    business_insights: list[str] = field(default_factory=list)
    trend_metrics: TrendMetrics = field(default_factory=TrendMetrics)
    kpi_cards: list[KpiCard] = field(default_factory=list)
    chart_data: dict[str, Any] = field(default_factory=dict)
    export_data: dict[str, Any] = field(default_factory=dict)
    # Backward-compatible flat dashboard map (derived once from executive + coverage)
    dashboard: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executive_summary": self.executive_summary.to_dict(),
            "platform_summary": [p.to_dict() for p in self.platform_summary],
            "outlet_summary": [o.to_dict() for o in self.outlet_summary],
            "top_performers": self.top_performers.to_dict(),
            "financial_summary": self.financial_summary.to_dict(),
            "platform_comparison": self.platform_comparison.to_dict(),
            "business_insights": list(self.business_insights),
            "trend_metrics": self.trend_metrics.to_dict(),
            "kpi_cards": [c.to_dict() for c in self.kpi_cards],
            "chart_data": self.chart_data,
            "export_data": self.export_data,
            "dashboard": self.dashboard,
        }
