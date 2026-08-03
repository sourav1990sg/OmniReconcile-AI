"""Sprint 8 — Business Intelligence & Decision Engine models.

Consumes AnalyticsReport. Produces BusinessIntelligenceReport.
No AI — deterministic rules only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["Low", "Medium", "High", "Critical"]
CardCategory = Literal[
    "insight",
    "recommendation",
    "financial_risk",
    "commercial_risk",
    "operations_risk",
    "recovery_opportunity",
    "outlet_opportunity",
    "platform_opportunity",
    "priority",
]


def _round2(value: float) -> float:
    return round(float(value), 2)


@dataclass
class IntelligenceCard:
    """Single decision artifact — every insight/risk/opportunity/recommendation."""

    id: str
    title: str
    description: str
    severity: Severity
    business_impact: str
    recommended_action: str
    supporting_metrics: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # 0–1 deterministic certainty of the rule match
    category: CardCategory = "insight"
    domain: str = "general"  # finance | commercial | operations | recovery | outlet | platform

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = _round2(float(self.confidence) * 100) / 100
        metrics = {}
        for k, v in (self.supporting_metrics or {}).items():
            metrics[k] = _round2(v) if isinstance(v, float) else v
        payload["supporting_metrics"] = metrics
        return payload


@dataclass
class PriorityAction:
    """Ranked next step for executives — answers 'what should I do next?'."""

    rank: int
    title: str
    description: str
    severity: Severity
    recommended_action: str
    business_impact: str
    owner: str  # CEO | CFO | Finance | Operations | Commercial
    confidence: float = 1.0
    source_card_ids: list[str] = field(default_factory=list)
    supporting_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = _round2(float(self.confidence) * 100) / 100
        metrics = {}
        for k, v in (self.supporting_metrics or {}).items():
            metrics[k] = _round2(v) if isinstance(v, float) else v
        payload["supporting_metrics"] = metrics
        return payload


@dataclass
class ExecutiveDecisionSummary:
    """Headline narrative for CEO/CFO — decisions first, metrics as support."""

    headline: str = ""
    situation: str = ""
    primary_risk: str = ""
    primary_opportunity: str = ""
    next_action: str = ""
    risk_count: int = 0
    opportunity_count: int = 0
    high_priority_count: int = 0
    # Display-only metrics copied from AnalyticsReport (never recomputed)
    online_sales: float = 0.0
    platform_payout: float = 0.0
    recoverable_amount: float = 0.0
    settlement_coverage_pct: float = 0.0
    agreement_violations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "situation": self.situation,
            "primary_risk": self.primary_risk,
            "primary_opportunity": self.primary_opportunity,
            "next_action": self.next_action,
            "risk_count": self.risk_count,
            "opportunity_count": self.opportunity_count,
            "high_priority_count": self.high_priority_count,
            "online_sales": _round2(self.online_sales),
            "platform_payout": _round2(self.platform_payout),
            "recoverable_amount": _round2(self.recoverable_amount),
            "settlement_coverage_pct": _round2(self.settlement_coverage_pct),
            "agreement_violations": self.agreement_violations,
        }


@dataclass
class BusinessIntelligenceReport:
    """
    Decision layer over AnalyticsReport.

    Dashboards render this object for insights, risks, opportunities,
    recommendations, and priority actions. Numeric KPIs/charts are
    passed through via `analytics` (AnalyticsReport.to_dict()) — never recalculated.
    """

    executive_summary: ExecutiveDecisionSummary = field(default_factory=ExecutiveDecisionSummary)
    financial_risks: list[IntelligenceCard] = field(default_factory=list)
    commercial_risks: list[IntelligenceCard] = field(default_factory=list)
    operations_risks: list[IntelligenceCard] = field(default_factory=list)
    recovery_opportunities: list[IntelligenceCard] = field(default_factory=list)
    outlet_opportunities: list[IntelligenceCard] = field(default_factory=list)
    platform_opportunities: list[IntelligenceCard] = field(default_factory=list)
    priority_actions: list[PriorityAction] = field(default_factory=list)
    insight_cards: list[IntelligenceCard] = field(default_factory=list)
    recommendation_cards: list[IntelligenceCard] = field(default_factory=list)
    risk_cards: list[IntelligenceCard] = field(default_factory=list)
    opportunity_cards: list[IntelligenceCard] = field(default_factory=list)
    analytics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executive_summary": self.executive_summary.to_dict(),
            "financial_risks": [c.to_dict() for c in self.financial_risks],
            "commercial_risks": [c.to_dict() for c in self.commercial_risks],
            "operations_risks": [c.to_dict() for c in self.operations_risks],
            "recovery_opportunities": [c.to_dict() for c in self.recovery_opportunities],
            "outlet_opportunities": [c.to_dict() for c in self.outlet_opportunities],
            "platform_opportunities": [c.to_dict() for c in self.platform_opportunities],
            "priority_actions": [p.to_dict() for p in self.priority_actions],
            "insight_cards": [c.to_dict() for c in self.insight_cards],
            "recommendation_cards": [c.to_dict() for c in self.recommendation_cards],
            "risk_cards": [c.to_dict() for c in self.risk_cards],
            "opportunity_cards": [c.to_dict() for c in self.opportunity_cards],
            "analytics": self.analytics,
        }
