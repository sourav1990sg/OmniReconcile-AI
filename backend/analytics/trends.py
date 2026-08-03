"""Trend metrics from day buckets (deterministic)."""

from __future__ import annotations

from backend.analytics.aggregations import AggregationIndex
from backend.analytics.models import TrendMetrics


def build_trends(index: AggregationIndex) -> TrendMetrics:
    days = sorted(d for d in index.by_day.keys() if d != "unknown")
    orders_by_day = []
    sales_by_day = []
    payout_by_day = []
    for day in days:
        b = index.by_day[day]
        orders_by_day.append({"date": day, "orders": b.matched_count})
        sales_by_day.append({"date": day, "sales": round(b.sales, 2)})
        payout_by_day.append({"date": day, "payout": round(b.platform_payout, 2)})
    return TrendMetrics(
        orders_by_day=orders_by_day,
        sales_by_day=sales_by_day,
        payout_by_day=payout_by_day,
    )
