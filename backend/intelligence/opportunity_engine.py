"""Recovery, outlet, and platform opportunity cards — deterministic."""

from __future__ import annotations

from backend.analytics.models import AnalyticsReport
from backend.intelligence.models import IntelligenceCard
from backend.intelligence import rules as R


def build_recovery_opportunities(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    fin = report.financial_summary
    name, amount, share = R.recoverable_outlet_share(report)

    if fin.recoverable > 0:
        sev = R.severity_from_recoverable(fin.recoverable, share)
        cards.append(
            IntelligenceCard(
                id="opp-total-recovery",
                title="Recoverable cash opportunity",
                description=(
                    f"₹{fin.recoverable:,.2f} is classified as recoverable underpayment."
                ),
                severity=sev,
                business_impact="Direct cash recovery if disputes succeed.",
                recommended_action="Prioritize dispute packages by outlet recoverable amount.",
                supporting_metrics={"recoverable": fin.recoverable},
                confidence=1.0,
                category="recovery_opportunity",
                domain="recovery",
            )
        )

        if name and amount > 0:
            cards.append(
                IntelligenceCard(
                    id="opp-outlet-recovery",
                    title=f"Recovery focus — {name}",
                    description=(
                        f"{name} contributes {share:.0f}% of recoverable revenue "
                        f"(₹{amount:,.2f})."
                    ),
                    severity=R.severity_from_recoverable(amount, share),
                    business_impact="Concentrated recovery improves dispute ROI.",
                    recommended_action="Investigate settlement.",
                    supporting_metrics={
                        "outlet": name,
                        "outlet_recoverable": amount,
                        "share_pct": share,
                        "total_recoverable": fin.recoverable,
                    },
                    confidence=1.0,
                    category="recovery_opportunity",
                    domain="recovery",
                )
            )

        # Platform-level recovery
        for p in sorted(
            report.platform_summary,
            key=lambda x: x.recoverable_amount,
            reverse=True,
        ):
            if p.recoverable_amount <= 0:
                continue
            plat_share = R.pct_of(p.recoverable_amount, fin.recoverable)
            cards.append(
                IntelligenceCard(
                    id=f"opp-platform-recovery-{p.platform.lower()}",
                    title=f"{p.platform} recoverable exposure",
                    description=(
                        f"{p.platform} holds ₹{p.recoverable_amount:,.2f} recoverable "
                        f"({plat_share:.0f}% of total)."
                    ),
                    severity=R.severity_from_recoverable(p.recoverable_amount, plat_share),
                    business_impact="Platform-specific dispute templates speed recovery.",
                    recommended_action=f"File {p.platform} support tickets for shortfall orders.",
                    supporting_metrics={
                        "platform": p.platform,
                        "recoverable": p.recoverable_amount,
                        "share_pct": plat_share,
                    },
                    confidence=1.0,
                    category="recovery_opportunity",
                    domain="recovery",
                )
            )
            break  # top platform only to avoid noise

    return cards


def build_outlet_opportunities(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    tops = report.top_performers

    if tops.highest_average_order_value:
        outlet = next(
            (o for o in report.outlet_summary if o.outlet == tops.highest_average_order_value),
            None,
        )
        cards.append(
            IntelligenceCard(
                id="opp-high-aov-outlet",
                title=f"Scale high-AOV outlet — {tops.highest_average_order_value}",
                description=(
                    f"{tops.highest_average_order_value} has the highest average order value."
                ),
                severity="Low",
                business_impact="Marketing spend here yields higher ticket sizes.",
                recommended_action="Increase marketing spend.",
                supporting_metrics={
                    "outlet": tops.highest_average_order_value,
                    "average_order_value": outlet.average_order_value if outlet else 0.0,
                    "sales": outlet.sales if outlet else 0.0,
                },
                confidence=1.0 if outlet else 0.85,
                category="outlet_opportunity",
                domain="outlet",
            )
        )

    if tops.highest_online_sales_outlet:
        outlet = next(
            (o for o in report.outlet_summary if o.outlet == tops.highest_online_sales_outlet),
            None,
        )
        cards.append(
            IntelligenceCard(
                id="opp-top-sales-outlet",
                title=f"Protect top sales outlet — {tops.highest_online_sales_outlet}",
                description=(
                    f"{tops.highest_online_sales_outlet} generated the highest online sales."
                ),
                severity="Low",
                business_impact="Volume leader; downtime has outsized revenue impact.",
                recommended_action="Ensure peak staffing and platform menu completeness.",
                supporting_metrics={
                    "outlet": tops.highest_online_sales_outlet,
                    "sales": outlet.sales if outlet else 0.0,
                    "orders": outlet.total_orders if outlet else 0,
                },
                confidence=1.0 if outlet else 0.85,
                category="outlet_opportunity",
                domain="outlet",
            )
        )

    # Lift lagging AOV outlets toward top
    if len(report.outlet_summary) >= 2:
        ranked = sorted(report.outlet_summary, key=lambda o: o.average_order_value, reverse=True)
        best, worst = ranked[0], ranked[-1]
        if best.average_order_value > worst.average_order_value > 0:
            gap = round(best.average_order_value - worst.average_order_value, 2)
            cards.append(
                IntelligenceCard(
                    id="opp-aov-gap",
                    title=f"Close AOV gap — {worst.outlet}",
                    description=(
                        f"{worst.outlet} AOV is ₹{gap:,.2f} below {best.outlet}."
                    ),
                    severity="Medium" if gap >= 50 else "Low",
                    business_impact="Upsell and combo strategies can lift contribution.",
                    recommended_action="Test bundle pricing and add-ons at the lagging outlet.",
                    supporting_metrics={
                        "best_outlet": best.outlet,
                        "best_aov": best.average_order_value,
                        "lagging_outlet": worst.outlet,
                        "lagging_aov": worst.average_order_value,
                        "aov_gap": gap,
                    },
                    confidence=1.0,
                    category="outlet_opportunity",
                    domain="outlet",
                )
            )

    return cards


def build_platform_opportunities(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    cmp_ = report.platform_comparison
    by_name = R.platform_by_name(report)

    # Prefer lower-commission platform for promo push
    higher, lower, gap = R.commission_gap_pp(report)
    if gap >= R.COMMISSION_GAP_MEDIUM_PP and lower in by_name:
        cards.append(
            IntelligenceCard(
                id="opp-shift-to-lower-commission",
                title=f"Prefer growth on {lower}",
                description=(
                    f"{higher} commission is {gap:.1f}% higher than {lower}. "
                    f"Incremental volume on {lower} nets more payout."
                ),
                severity=R.severity_from_gap(gap),
                business_impact="Same GMV yields higher net on the lower-commission platform.",
                recommended_action=f"Shift promo budget toward {lower} where demand allows.",
                supporting_metrics={
                    "higher_platform": higher,
                    "lower_platform": lower,
                    "commission_gap_pp": round(gap, 2),
                },
                confidence=1.0,
                category="platform_opportunity",
                domain="platform",
            )
        )

    # Underweight platform with room to grow
    if cmp_.swiggy_revenue_share_pct and cmp_.zomato_revenue_share_pct:
        if cmp_.swiggy_revenue_share_pct < 35:
            cards.append(
                IntelligenceCard(
                    id="opp-grow-swiggy",
                    title="Grow Swiggy share",
                    description=(
                        f"Swiggy is only {cmp_.swiggy_revenue_share_pct:.0f}% of online revenue."
                    ),
                    severity="Low",
                    business_impact="Diversification reduces single-platform dependency.",
                    recommended_action="Increase Swiggy visibility and local ads.",
                    supporting_metrics={
                        "swiggy_revenue_share_pct": cmp_.swiggy_revenue_share_pct,
                        "swiggy_aov": cmp_.swiggy_aov,
                    },
                    confidence=0.9,
                    category="platform_opportunity",
                    domain="platform",
                )
            )
        if cmp_.zomato_revenue_share_pct < 35:
            cards.append(
                IntelligenceCard(
                    id="opp-grow-zomato",
                    title="Grow Zomato share",
                    description=(
                        f"Zomato is only {cmp_.zomato_revenue_share_pct:.0f}% of online revenue."
                    ),
                    severity="Low",
                    business_impact="Diversification reduces single-platform dependency.",
                    recommended_action="Increase Zomato visibility and local ads.",
                    supporting_metrics={
                        "zomato_revenue_share_pct": cmp_.zomato_revenue_share_pct,
                        "zomato_aov": cmp_.zomato_aov,
                    },
                    confidence=0.9,
                    category="platform_opportunity",
                    domain="platform",
                )
            )

    # Promo recovery already in settlements — highlight if material
    for p in report.platform_summary:
        if p.promo_recovery >= 1_000:
            cards.append(
                IntelligenceCard(
                    id=f"opp-promo-recovery-{p.platform.lower()}",
                    title=f"{p.platform} promo recovery realized",
                    description=(
                        f"{p.platform} promo recovery is ₹{p.promo_recovery:,.2f}."
                    ),
                    severity="Low",
                    business_impact="Confirm promo claims are fully settled each cycle.",
                    recommended_action="Reconcile promo claims against campaign tracker.",
                    supporting_metrics={
                        "platform": p.platform,
                        "promo_recovery": p.promo_recovery,
                    },
                    confidence=1.0,
                    category="platform_opportunity",
                    domain="platform",
                )
            )

    return cards


def build_all_opportunities(report: AnalyticsReport) -> tuple[
    list[IntelligenceCard],
    list[IntelligenceCard],
    list[IntelligenceCard],
]:
    return (
        build_recovery_opportunities(report),
        build_outlet_opportunities(report),
        build_platform_opportunities(report),
    )
