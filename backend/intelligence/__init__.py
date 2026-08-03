"""
Sprint 8 — Business Intelligence & Decision Engine.

Consumes AnalyticsReport. Emits BusinessIntelligenceReport.
Deterministic rules only — no AI.
"""

from backend.intelligence.models import BusinessIntelligenceReport, IntelligenceCard
from backend.intelligence.report import build_business_intelligence_report


class BusinessIntelligenceEngine:
    """Transform AnalyticsReport into actionable decisions."""

    def build(self, analytics_report) -> BusinessIntelligenceReport:
        return build_business_intelligence_report(analytics_report)


__all__ = [
    "BusinessIntelligenceEngine",
    "BusinessIntelligenceReport",
    "IntelligenceCard",
    "build_business_intelligence_report",
]
