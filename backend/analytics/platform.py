"""Platform analytics section — reshapes AggregationIndex only."""

from __future__ import annotations

from backend.analytics.aggregations import AggregationIndex, pct
from backend.analytics.models import PlatformComparison, PlatformSummary


def build_platform_summaries(index: AggregationIndex) -> list[PlatformSummary]:
    out: list[PlatformSummary] = []
    for name in sorted(index.by_platform.keys()):
        b = index.by_platform[name]
        matched = b.matched_count or 0
        out.append(
            PlatformSummary(
                platform=name,
                order_count=b.order_count,
                sales=round(b.sales, 2),
                gross_order_value=round(b.gross_order_value, 2),
                platform_payout=round(b.platform_payout, 2),
                average_order_value=b.average_order_value(),
                commission=round(b.commission, 2),
                government_charges=round(b.government_charges, 2),
                tds=round(b.tds, 2),
                tcs=round(b.tcs, 2),
                gst=round(b.gst, 2),
                restaurant_discount=round(b.restaurant_discount, 2),
                platform_discount=round(b.platform_discount, 2),
                promo_recovery=round(b.promo_recovery, 2),
                customer_compensation=round(b.customer_compensation, 2),
                other_deductions=round(b.other_deductions, 2),
                net_deductions=round(b.net_deductions, 2),
                recoverable_amount=round(b.recoverable, 2),
                settlement_coverage_pct=pct(matched, b.order_count),
                payment_match_pct=pct(b.payment_match, matched),
                agreement_verification_pct=pct(b.agreement_verified, matched),
                payment_match_orders=b.payment_match,
                agreement_verified_orders=b.agreement_verified,
            )
        )
    return out


def build_platform_comparison(index: AggregationIndex) -> PlatformComparison:
    sw = index.by_platform.get("Swiggy")
    zo = index.by_platform.get("Zomato")
    total_orders = (sw.matched_count if sw else 0) + (zo.matched_count if zo else 0)
    total_sales = (sw.sales if sw else 0.0) + (zo.sales if zo else 0.0)
    total_payout = (sw.platform_payout if sw else 0.0) + (zo.platform_payout if zo else 0.0)

    def commission_rate(bucket) -> float:
        if not bucket or not bucket.gross_order_value:
            return 0.0
        return pct(bucket.commission, bucket.gross_order_value)

    return PlatformComparison(
        swiggy_order_share_pct=pct(sw.matched_count if sw else 0, total_orders),
        zomato_order_share_pct=pct(zo.matched_count if zo else 0, total_orders),
        swiggy_revenue_share_pct=pct(sw.sales if sw else 0.0, total_sales),
        zomato_revenue_share_pct=pct(zo.sales if zo else 0.0, total_sales),
        swiggy_payout_share_pct=pct(sw.platform_payout if sw else 0.0, total_payout),
        zomato_payout_share_pct=pct(zo.platform_payout if zo else 0.0, total_payout),
        swiggy_commission_pct=commission_rate(sw),
        zomato_commission_pct=commission_rate(zo),
        swiggy_aov=sw.average_order_value() if sw else 0.0,
        zomato_aov=zo.average_order_value() if zo else 0.0,
    )
