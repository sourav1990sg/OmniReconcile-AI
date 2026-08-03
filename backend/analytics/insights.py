"""Deterministic business insights — no AI."""

from __future__ import annotations

from backend.analytics.models import (
    FinancialSummary,
    OutletSummary,
    PlatformComparison,
    PlatformSummary,
    TopPerformers,
)


def build_insights(
    *,
    platforms: list[PlatformSummary],
    outlets: list[OutletSummary],
    comparison: PlatformComparison,
    tops: TopPerformers,
    financial: FinancialSummary,
) -> list[str]:
    insights: list[str] = []

    by_name = {p.platform: p for p in platforms}
    zo = by_name.get("Zomato")
    sw = by_name.get("Swiggy")

    if zo and comparison.zomato_revenue_share_pct:
        insights.append(
            f"Zomato contributes {comparison.zomato_revenue_share_pct:.0f}% of online revenue."
        )
    if sw and comparison.swiggy_revenue_share_pct:
        insights.append(
            f"Swiggy contributes {comparison.swiggy_revenue_share_pct:.0f}% of online revenue."
        )

    if tops.highest_online_sales_outlet:
        insights.append(
            f"{tops.highest_online_sales_outlet} generated the highest online sales."
        )
    if tops.highest_average_order_value:
        insights.append(
            f"{tops.highest_average_order_value} has the highest average order value."
        )

    if sw and zo:
        if comparison.swiggy_commission_pct > comparison.zomato_commission_pct:
            insights.append("Swiggy average commission is higher than Zomato.")
        elif comparison.zomato_commission_pct > comparison.swiggy_commission_pct:
            insights.append("Zomato average commission is higher than Swiggy.")

    if financial.recoverable > 0 and tops.highest_recoverable_amount:
        # Concentration check
        top_rec = next(
            (o for o in outlets if o.outlet == tops.highest_recoverable_amount),
            None,
        )
        if top_rec and financial.recoverable > 0:
            share = round((top_rec.recoverable_amount / financial.recoverable) * 100, 1)
            if share >= 50:
                insights.append(
                    f"Recoverable amount is concentrated in {top_rec.outlet} ({share}%)."
                )
            else:
                insights.append(
                    f"Highest recoverable amount is at {top_rec.outlet}."
                )
    elif financial.recoverable == 0:
        insights.append("No unexplained recoverable amount in this period.")

    if tops.most_cancelled_outlet:
        cancelled = next(
            (o for o in outlets if o.outlet == tops.most_cancelled_outlet),
            None,
        )
        if cancelled and cancelled.cancelled > 0:
            insights.append(
                f"{tops.most_cancelled_outlet} has the most cancelled orders ({cancelled.cancelled})."
            )

    return insights
