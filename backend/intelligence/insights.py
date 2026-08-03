"""Deterministic insight cards from AnalyticsReport — no AI."""

from __future__ import annotations

from backend.analytics.models import AnalyticsReport
from backend.intelligence.models import IntelligenceCard
from backend.intelligence import rules as R


def build_insight_cards(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    ex = report.executive_summary
    cmp_ = report.platform_comparison
    tops = report.top_performers
    fin = report.financial_summary

    # Platform revenue share
    if cmp_.zomato_revenue_share_pct > 0:
        cards.append(
            IntelligenceCard(
                id="insight-zomato-revenue-share",
                title="Zomato revenue contribution",
                description=(
                    f"Zomato contributes {cmp_.zomato_revenue_share_pct:.0f}% of online revenue."
                ),
                severity="Low" if cmp_.zomato_revenue_share_pct < R.REVENUE_SHARE_DOMINANT else "Medium",
                business_impact="Platform mix drives negotiation leverage and promo strategy.",
                recommended_action="Align inventory and campaign spend with Zomato demand.",
                supporting_metrics={
                    "zomato_revenue_share_pct": cmp_.zomato_revenue_share_pct,
                    "swiggy_revenue_share_pct": cmp_.swiggy_revenue_share_pct,
                },
                confidence=R.confidence_for_metrics(cmp_.zomato_revenue_share_pct),
                category="insight",
                domain="platform",
            )
        )
    if cmp_.swiggy_revenue_share_pct > 0:
        cards.append(
            IntelligenceCard(
                id="insight-swiggy-revenue-share",
                title="Swiggy revenue contribution",
                description=(
                    f"Swiggy contributes {cmp_.swiggy_revenue_share_pct:.0f}% of online revenue."
                ),
                severity="Low" if cmp_.swiggy_revenue_share_pct < R.REVENUE_SHARE_DOMINANT else "Medium",
                business_impact="Concentration risk if one platform dominates sales.",
                recommended_action="Balance acquisition across platforms where share exceeds 65%.",
                supporting_metrics={
                    "swiggy_revenue_share_pct": cmp_.swiggy_revenue_share_pct,
                    "zomato_revenue_share_pct": cmp_.zomato_revenue_share_pct,
                },
                confidence=R.confidence_for_metrics(cmp_.swiggy_revenue_share_pct),
                category="insight",
                domain="platform",
            )
        )

    # Commission gap — example: Swiggy commission is 2.8% higher than Zomato
    higher, lower, gap = R.commission_gap_pp(report)
    if gap > 0 and (cmp_.swiggy_commission_pct > 0 or cmp_.zomato_commission_pct > 0):
        sev = R.severity_from_gap(gap)
        cards.append(
            IntelligenceCard(
                id="insight-commission-gap",
                title=f"{higher} commission premium vs {lower}",
                description=(
                    f"{higher} commission is {gap:.1f}% higher than {lower}."
                ),
                severity=sev,
                business_impact=(
                    f"Higher effective commission on {higher} reduces net payout "
                    f"relative to {lower}."
                ),
                recommended_action="Review commercial agreement.",
                supporting_metrics={
                    "swiggy_commission_pct": cmp_.swiggy_commission_pct,
                    "zomato_commission_pct": cmp_.zomato_commission_pct,
                    "commission_gap_pp": round(gap, 2),
                    "higher_platform": higher,
                },
                confidence=R.confidence_for_metrics(
                    cmp_.swiggy_commission_pct, cmp_.zomato_commission_pct
                ),
                category="insight",
                domain="commercial",
            )
        )

    # Top sales outlet
    if tops.highest_online_sales_outlet:
        outlet = next(
            (o for o in report.outlet_summary if o.outlet == tops.highest_online_sales_outlet),
            None,
        )
        cards.append(
            IntelligenceCard(
                id="insight-top-sales-outlet",
                title="Highest revenue outlet",
                description=(
                    f"{tops.highest_online_sales_outlet} generated the highest online sales."
                ),
                severity="Low",
                business_impact="Anchor outlet for volume and brand presence.",
                recommended_action="Protect service levels and inventory at this outlet.",
                supporting_metrics={
                    "outlet": tops.highest_online_sales_outlet,
                    "sales": outlet.sales if outlet else 0.0,
                },
                confidence=1.0 if outlet else 0.85,
                category="insight",
                domain="outlet",
            )
        )

    # Highest AOV — example: Downtown Mall has highest AOV
    if tops.highest_average_order_value:
        outlet = next(
            (o for o in report.outlet_summary if o.outlet == tops.highest_average_order_value),
            None,
        )
        cards.append(
            IntelligenceCard(
                id="insight-highest-aov",
                title="Highest average order value",
                description=(
                    f"{tops.highest_average_order_value} has the highest average order value."
                ),
                severity="Low",
                business_impact="High AOV outlets maximize margin per order.",
                recommended_action="Increase marketing spend.",
                supporting_metrics={
                    "outlet": tops.highest_average_order_value,
                    "average_order_value": outlet.average_order_value if outlet else 0.0,
                },
                confidence=1.0 if outlet else 0.85,
                category="insight",
                domain="outlet",
            )
        )

    # Recoverable concentration — example: Patuli contributes 42% of recoverable
    name, amount, share = R.recoverable_outlet_share(report)
    if fin.recoverable > 0 and name:
        sev = R.severity_from_recoverable(amount, share)
        cards.append(
            IntelligenceCard(
                id="insight-recoverable-concentration",
                title="Recoverable concentration",
                description=(
                    f"{name} contributes {share:.0f}% of recoverable revenue."
                    if share >= R.RECOVERABLE_SHARE_MEDIUM
                    else f"Highest recoverable amount is at {name}."
                ),
                severity=sev,
                business_impact=f"₹{amount:,.2f} unexplained underpayment exposure.",
                recommended_action="Investigate settlement.",
                supporting_metrics={
                    "outlet": name,
                    "outlet_recoverable": amount,
                    "total_recoverable": fin.recoverable,
                    "share_pct": share,
                },
                confidence=R.confidence_for_metrics(amount, fin.recoverable),
                category="insight",
                domain="recovery",
            )
        )
    elif fin.recoverable == 0:
        cards.append(
            IntelligenceCard(
                id="insight-no-recoverable",
                title="No recoverable exposure",
                description="No unexplained recoverable amount in this period.",
                severity="Low",
                business_impact="Settlement math aligns with calculated payouts.",
                recommended_action="Maintain current reconciliation controls.",
                supporting_metrics={"recoverable": 0.0},
                confidence=1.0,
                category="insight",
                domain="finance",
            )
        )

    # Settlement coverage
    if ex.settlement_coverage_pct > 0:
        cov_sev = R.severity_from_coverage(ex.settlement_coverage_pct)
        cards.append(
            IntelligenceCard(
                id="insight-settlement-coverage",
                title="Settlement coverage",
                description=(
                    f"Settlement coverage is {ex.settlement_coverage_pct:.1f}%."
                ),
                severity=cov_sev or "Low",
                business_impact="Coverage below 95% leaves orders without settlement proof.",
                recommended_action=(
                    "Chase missing settlement files."
                    if cov_sev
                    else "Continue monitoring unmatched POS."
                ),
                supporting_metrics={
                    "settlement_coverage_pct": ex.settlement_coverage_pct,
                    "matched_orders": ex.matched_orders,
                    "total_pos_orders": ex.total_pos_orders,
                },
                confidence=1.0,
                category="insight",
                domain="finance",
            )
        )

    # Cancellations
    if tops.most_cancelled_outlet:
        cancelled = next(
            (o for o in report.outlet_summary if o.outlet == tops.most_cancelled_outlet),
            None,
        )
        if cancelled and cancelled.cancelled > 0:
            cards.append(
                IntelligenceCard(
                    id="insight-most-cancelled",
                    title="Cancellation hotspot",
                    description=(
                        f"{tops.most_cancelled_outlet} has the most cancelled orders "
                        f"({cancelled.cancelled})."
                    ),
                    severity="Medium" if cancelled.cancelled >= 5 else "Low",
                    business_impact="Cancellations reduce fulfilled revenue and waste prep.",
                    recommended_action="Review kitchen capacity and acceptance SLA at this outlet.",
                    supporting_metrics={
                        "outlet": tops.most_cancelled_outlet,
                        "cancelled": cancelled.cancelled,
                    },
                    confidence=1.0,
                    category="insight",
                    domain="operations",
                )
            )

    return cards
