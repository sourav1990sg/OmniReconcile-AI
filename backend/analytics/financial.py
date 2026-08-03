"""Financial summary — single reshape of global MetricBucket."""

from __future__ import annotations

from backend.analytics.aggregations import AggregationIndex
from backend.analytics.models import FinancialSummary


def build_financial_summary(index: AggregationIndex) -> FinancialSummary:
    g = index.global_bucket
    return FinancialSummary(
        total_pos_sales=round(g.sales, 2),
        gross_order_value=round(g.gross_order_value, 2),
        total_commission=round(g.commission, 2),
        total_payment_fees=round(g.payment_fees, 2),
        total_gst=round(g.gst, 2),
        total_government_charges=round(g.government_charges, 2),
        total_tcs=round(g.tcs, 2),
        total_tds=round(g.tds, 2),
        total_platform_deductions=round(g.net_deductions, 2),
        total_promo_recovery=round(g.promo_recovery, 2),
        total_customer_compensation=round(g.customer_compensation, 2),
        net_platform_payout=round(g.platform_payout, 2),
        recoverable=round(g.recoverable, 2),
    )
