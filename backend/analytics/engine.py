"""AnalyticsEngine — builds AnalyticsReport from reconciled rows (read-only)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from backend.analytics.aggregations import AggregationIndex
from backend.analytics.financial import build_financial_summary
from backend.analytics.insights import build_insights
from backend.analytics.models import AnalyticsReport
from backend.analytics.outlet import build_outlet_summaries, build_top_performers
from backend.analytics.platform import build_platform_comparison, build_platform_summaries
from backend.analytics.report import (
    build_chart_data,
    build_executive,
    build_export_data,
    build_kpi_cards,
    flatten_dashboard,
)
from backend.analytics.trends import build_trends


class AnalyticsEngine:
    """
    Convert reconciled row data into Business Intelligence.

    Input: list of reconciliation API rows (+ optional metadata).
    Output: AnalyticsReport — single source of truth for KPIs.
    """

    def build(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        pos_metadata: Mapping[str, Any] | None = None,
        settlement_metadata: Mapping[str, Any] | None = None,
        status_counts: Mapping[str, int] | None = None,
        recon_totals: Mapping[str, Any] | None = None,
    ) -> AnalyticsReport:
        index = AggregationIndex.build(list(rows))
        executive = build_executive(
            index,
            pos_meta=pos_metadata,
            settle_meta=settlement_metadata,
            status_counts=status_counts,
        )
        platforms = build_platform_summaries(index)
        outlets = build_outlet_summaries(index)
        tops = build_top_performers(outlets)
        financial = build_financial_summary(index)
        comparison = build_platform_comparison(index)
        insights = build_insights(
            platforms=platforms,
            outlets=outlets,
            comparison=comparison,
            tops=tops,
            financial=financial,
        )
        trends = build_trends(index)
        kpi_cards = build_kpi_cards(executive, financial)
        chart_data = build_chart_data(platforms, outlets, executive)
        dashboard = flatten_dashboard(executive, recon_totals=recon_totals)

        report = AnalyticsReport(
            executive_summary=executive,
            platform_summary=platforms,
            outlet_summary=outlets,
            top_performers=tops,
            financial_summary=financial,
            platform_comparison=comparison,
            business_insights=insights,
            trend_metrics=trends,
            kpi_cards=kpi_cards,
            chart_data=chart_data,
            dashboard=dashboard,
        )
        report.export_data = build_export_data(report)
        return report
