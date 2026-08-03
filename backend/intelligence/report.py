"""Assemble BusinessIntelligenceReport from AnalyticsReport."""

from __future__ import annotations

from backend.analytics.models import AnalyticsReport
from backend.intelligence.insights import build_insight_cards
from backend.intelligence.models import (
    BusinessIntelligenceReport,
    ExecutiveDecisionSummary,
    IntelligenceCard,
)
from backend.intelligence.opportunity_engine import build_all_opportunities
from backend.intelligence.priority_engine import build_priority_actions
from backend.intelligence.recommendations import build_recommendation_cards
from backend.intelligence.risk_engine import build_all_risks
from backend.intelligence.rules import SEVERITY_RANK


def _primary_title(cards: list[IntelligenceCard]) -> str:
    if not cards:
        return "None identified"
    top = max(cards, key=lambda c: (SEVERITY_RANK[c.severity], c.confidence))
    return top.title


def build_executive_decision_summary(
    report: AnalyticsReport,
    *,
    risks: list[IntelligenceCard],
    opportunities: list[IntelligenceCard],
    priority_actions: list,
) -> ExecutiveDecisionSummary:
    ex = report.executive_summary
    fin = report.financial_summary
    high = [c for c in risks if SEVERITY_RANK[c.severity] >= 3]
    next_action = (
        priority_actions[0].recommended_action
        if priority_actions
        else "Review AnalyticsReport KPIs and confirm settlement completeness."
    )
    if high:
        headline = f"{len(high)} high-priority risk(s) require action this cycle."
    elif fin.recoverable > 0:
        headline = f"₹{fin.recoverable:,.2f} recoverable opportunity identified."
    else:
        headline = "Financials are stable — focus on growth opportunities."

    situation = (
        f"₹{ex.total_online_sales:,.2f} online sales · "
        f"{ex.matched_orders} matched · "
        f"{ex.settlement_coverage_pct:.1f}% settlement coverage · "
        f"₹{ex.recoverable_amount:,.2f} recoverable."
    )

    return ExecutiveDecisionSummary(
        headline=headline,
        situation=situation,
        primary_risk=_primary_title(risks),
        primary_opportunity=_primary_title(opportunities),
        next_action=next_action,
        risk_count=len(risks),
        opportunity_count=len(opportunities),
        high_priority_count=len(high),
        online_sales=ex.total_online_sales,
        platform_payout=ex.platform_payout,
        recoverable_amount=ex.recoverable_amount,
        settlement_coverage_pct=ex.settlement_coverage_pct,
        agreement_violations=ex.agreement_violations,
    )


def build_business_intelligence_report(
    analytics: AnalyticsReport,
) -> BusinessIntelligenceReport:
    """Pure deterministic transform: AnalyticsReport → BusinessIntelligenceReport."""
    financial_risks, commercial_risks, operations_risks = build_all_risks(analytics)
    recovery_opps, outlet_opps, platform_opps = build_all_opportunities(analytics)
    insight_cards = build_insight_cards(analytics)

    risks = [*financial_risks, *commercial_risks, *operations_risks]
    opportunities = [*recovery_opps, *outlet_opps, *platform_opps]

    recommendation_cards = build_recommendation_cards(
        insights=insight_cards,
        risks=risks,
        opportunities=opportunities,
    )
    priority_actions = build_priority_actions(
        risks=risks,
        opportunities=opportunities,
        recommendations=recommendation_cards,
    )
    executive = build_executive_decision_summary(
        analytics,
        risks=risks,
        opportunities=opportunities,
        priority_actions=priority_actions,
    )

    return BusinessIntelligenceReport(
        executive_summary=executive,
        financial_risks=financial_risks,
        commercial_risks=commercial_risks,
        operations_risks=operations_risks,
        recovery_opportunities=recovery_opps,
        outlet_opportunities=outlet_opps,
        platform_opportunities=platform_opps,
        priority_actions=priority_actions,
        insight_cards=insight_cards,
        recommendation_cards=recommendation_cards,
        risk_cards=risks,
        opportunity_cards=opportunities,
        analytics=analytics.to_dict(),
    )
