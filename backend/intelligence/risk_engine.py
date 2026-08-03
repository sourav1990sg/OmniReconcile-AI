"""Financial, commercial, and operations risk cards — deterministic."""

from __future__ import annotations

from backend.analytics.models import AnalyticsReport
from backend.intelligence.models import IntelligenceCard, Severity
from backend.intelligence import rules as R


def build_financial_risks(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    ex = report.executive_summary
    fin = report.financial_summary

    cov_sev = R.severity_from_coverage(ex.settlement_coverage_pct)
    if cov_sev:
        cards.append(
            IntelligenceCard(
                id="risk-settlement-coverage",
                title="Settlement coverage below target",
                description=(
                    f"Settlement coverage is {ex.settlement_coverage_pct:.1f}%, "
                    f"below the {R.COVERAGE_LOW:.0f}% target."
                ),
                severity=cov_sev,
                business_impact="Unsettled POS orders delay cash recognition and audit readiness.",
                recommended_action="Request missing settlement files from platforms.",
                supporting_metrics={
                    "settlement_coverage_pct": ex.settlement_coverage_pct,
                    "pending_orders": ex.pending_orders,
                    "not_reconciled_orders": ex.not_reconciled_orders,
                },
                confidence=1.0,
                category="financial_risk",
                domain="finance",
            )
        )

    if fin.recoverable > 0:
        sev = R.severity_from_recoverable(fin.recoverable, 0.0)
        if fin.recoverable >= R.RECOVERABLE_MEDIUM:
            sev = R.severity_from_recoverable(fin.recoverable, 100.0)
        cards.append(
            IntelligenceCard(
                id="risk-recoverable-exposure",
                title="Unexplained payout shortfall",
                description=(
                    f"Recoverable amount is ₹{fin.recoverable:,.2f} across "
                    f"{ex.financial_discrepancy_orders} discrepancy orders."
                ),
                severity=sev if fin.recoverable >= R.RECOVERABLE_MEDIUM else "Medium",
                business_impact="Cash leakage until shortfalls are disputed or written off.",
                recommended_action="Open platform disputes for FINANCIAL_DISCREPANCY orders.",
                supporting_metrics={
                    "recoverable": fin.recoverable,
                    "financial_discrepancy_orders": ex.financial_discrepancy_orders,
                },
                confidence=1.0,
                category="financial_risk",
                domain="finance",
            )
        )

    ded_ratio = R.pct_of(fin.total_platform_deductions, fin.gross_order_value)
    if fin.gross_order_value > 0 and ded_ratio >= 30:
        cards.append(
            IntelligenceCard(
                id="risk-high-deduction-ratio",
                title="High platform deduction ratio",
                description=(
                    f"Platform deductions are {ded_ratio:.1f}% of gross order value."
                ),
                severity="Medium" if ded_ratio < 40 else "High",
                business_impact="Elevated take-rate compresses restaurant contribution margin.",
                recommended_action="Benchmark deduction mix vs commercial agreement rates.",
                supporting_metrics={
                    "deduction_ratio_pct": ded_ratio,
                    "total_platform_deductions": fin.total_platform_deductions,
                    "gross_order_value": fin.gross_order_value,
                },
                confidence=R.confidence_for_metrics(fin.total_platform_deductions, fin.gross_order_value),
                category="financial_risk",
                domain="finance",
            )
        )

    return cards


def build_commercial_risks(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    ex = report.executive_summary
    cmp_ = report.platform_comparison

    if ex.agreement_violations >= R.VIOLATION_MEDIUM:
        sev: Severity = "High" if ex.agreement_violations >= R.VIOLATION_HIGH else "Medium"
        cards.append(
            IntelligenceCard(
                id="risk-agreement-violations",
                title="Commercial agreement violations",
                description=(
                    f"{ex.agreement_violations} orders flagged as AGREEMENT_VIOLATION."
                ),
                severity=sev,
                business_impact="Contract non-compliance may justify chargebacks or rate review.",
                recommended_action="Validate charged rates against uploaded commercial agreement.",
                supporting_metrics={
                    "agreement_violations": ex.agreement_violations,
                    "agreement_verified_orders": ex.agreement_verified_orders,
                },
                confidence=1.0,
                category="commercial_risk",
                domain="commercial",
            )
        )

    higher, lower, gap = R.commission_gap_pp(report)
    if gap >= R.COMMISSION_GAP_MEDIUM_PP:
        cards.append(
            IntelligenceCard(
                id="risk-commission-gap",
                title=f"{higher} commission exceeds {lower}",
                description=(
                    f"{higher} commission is {gap:.1f}% higher than {lower}."
                ),
                severity=R.severity_from_gap(gap),
                business_impact="Uneven commercial terms reduce net realization on the premium platform.",
                recommended_action="Review commercial agreement.",
                supporting_metrics={
                    "commission_gap_pp": round(gap, 2),
                    "swiggy_commission_pct": cmp_.swiggy_commission_pct,
                    "zomato_commission_pct": cmp_.zomato_commission_pct,
                },
                confidence=1.0,
                category="commercial_risk",
                domain="commercial",
            )
        )

    for p in report.platform_summary:
        if p.order_count > 0 and p.agreement_verification_pct < 50 and ex.agreement_verified_orders + ex.agreement_violations > 0:
            cards.append(
                IntelligenceCard(
                    id=f"risk-agreement-coverage-{p.platform.lower()}",
                    title=f"Low agreement verification — {p.platform}",
                    description=(
                        f"{p.platform} agreement verification is {p.agreement_verification_pct:.1f}%."
                    ),
                    severity="Medium",
                    business_impact="Limited contract coverage weakens dispute evidence.",
                    recommended_action="Upload or activate the current commercial agreement.",
                    supporting_metrics={
                        "platform": p.platform,
                        "agreement_verification_pct": p.agreement_verification_pct,
                    },
                    confidence=0.9,
                    category="commercial_risk",
                    domain="commercial",
                )
            )

    return cards


def build_operations_risks(report: AnalyticsReport) -> list[IntelligenceCard]:
    cards: list[IntelligenceCard] = []
    ex = report.executive_summary

    cancel_pct = R.pct_of(ex.cancelled_orders, ex.total_pos_orders)
    if cancel_pct >= R.CANCELLED_SHARE_MEDIUM:
        cards.append(
            IntelligenceCard(
                id="risk-cancellation-rate",
                title="Elevated cancellation rate",
                description=(
                    f"Cancelled orders are {cancel_pct:.1f}% of POS volume "
                    f"({ex.cancelled_orders} orders)."
                ),
                severity="High" if cancel_pct >= R.CANCELLED_SHARE_HIGH else "Medium",
                business_impact="Lost sales and wasted prep at peak windows.",
                recommended_action="Audit acceptance SLA and stockouts by outlet.",
                supporting_metrics={
                    "cancelled_orders": ex.cancelled_orders,
                    "cancelled_pct": cancel_pct,
                    "most_cancelled_outlet": report.top_performers.most_cancelled_outlet,
                },
                confidence=1.0,
                category="operations_risk",
                domain="operations",
            )
        )

    pending_pct = R.pct_of(ex.pending_orders, max(ex.eligible_orders, 1))
    if ex.pending_orders > 0 and pending_pct >= R.PENDING_SHARE_MEDIUM:
        cards.append(
            IntelligenceCard(
                id="risk-pending-orders",
                title="Pending reconciliation backlog",
                description=(
                    f"{ex.pending_orders} orders remain pending "
                    f"({pending_pct:.1f}% of eligible)."
                ),
                severity="High" if pending_pct >= R.PENDING_SHARE_HIGH else "Medium",
                business_impact="Backlog delays month-end close and recoverable identification.",
                recommended_action="Clear PENDING queue before next settlement cycle.",
                supporting_metrics={
                    "pending_orders": ex.pending_orders,
                    "pending_pct": pending_pct,
                },
                confidence=1.0,
                category="operations_risk",
                domain="operations",
            )
        )

    for o in report.outlet_summary:
        if o.total_orders >= 10 and o.payment_match_pct < R.PAYMENT_MATCH_LOW:
            cards.append(
                IntelligenceCard(
                    id=f"risk-payment-match-{o.outlet.lower().replace(' ', '-')}",
                    title=f"Low payment match — {o.outlet}",
                    description=(
                        f"{o.outlet} payment match is {o.payment_match_pct:.1f}%."
                    ),
                    severity="Medium",
                    business_impact="Outlet-level settlement noise increases finance review load.",
                    recommended_action="Spot-check settlement mapping for this outlet.",
                    supporting_metrics={
                        "outlet": o.outlet,
                        "payment_match_pct": o.payment_match_pct,
                        "total_orders": o.total_orders,
                    },
                    confidence=0.95,
                    category="operations_risk",
                    domain="operations",
                )
            )

    if report.top_performers.lowest_performing_outlet:
        low = next(
            (
                o
                for o in report.outlet_summary
                if o.outlet == report.top_performers.lowest_performing_outlet
            ),
            None,
        )
        if low and low.sales >= 0:
            cards.append(
                IntelligenceCard(
                    id="risk-lowest-outlet",
                    title="Lowest performing outlet",
                    description=(
                        f"{report.top_performers.lowest_performing_outlet} is the lowest "
                        f"sales outlet in this period."
                    ),
                    severity="Low",
                    business_impact="Underperforming outlets dilute brand and labor efficiency.",
                    recommended_action="Review local demand, menu, and platform visibility.",
                    supporting_metrics={
                        "outlet": report.top_performers.lowest_performing_outlet,
                        "sales": low.sales,
                        "orders": low.total_orders,
                    },
                    confidence=1.0,
                    category="operations_risk",
                    domain="operations",
                )
            )

    return cards


def build_all_risks(report: AnalyticsReport) -> tuple[
    list[IntelligenceCard],
    list[IntelligenceCard],
    list[IntelligenceCard],
]:
    return (
        build_financial_risks(report),
        build_commercial_risks(report),
        build_operations_risks(report),
    )
