"""Outlet analytics + top performers — reshapes AggregationIndex only."""

from __future__ import annotations

from backend.analytics.aggregations import AggregationIndex, pct
from backend.analytics.models import OutletSummary, TopPerformers


def build_outlet_summaries(index: AggregationIndex) -> list[OutletSummary]:
    out: list[OutletSummary] = []
    for name in sorted(index.by_outlet.keys()):
        b = index.by_outlet[name]
        plat_counts = dict(index.outlet_platform_orders.get(name, {}))
        matched = b.matched_count
        out.append(
            OutletSummary(
                outlet=name,
                swiggy_orders=int(plat_counts.get("Swiggy", 0)),
                zomato_orders=int(plat_counts.get("Zomato", 0)),
                total_orders=b.order_count,
                sales=round(b.sales, 2),
                gross_order_value=round(b.gross_order_value, 2),
                platform_payout=round(b.platform_payout, 2),
                average_order_value=b.average_order_value(),
                commission=round(b.commission, 2),
                recoverable_amount=round(b.recoverable, 2),
                payment_match_pct=pct(b.payment_match, matched),
                agreement_verified_pct=pct(b.agreement_verified, matched),
                cancelled=b.cancelled,
                pending=b.pending,
                platform_wise_orders=plat_counts,
            )
        )
    return out


def build_top_performers(outlets: list[OutletSummary]) -> TopPerformers:
    if not outlets:
        return TopPerformers()

    def best(key: str, *, reverse: bool = True) -> str | None:
        ranked = sorted(outlets, key=lambda o: getattr(o, key), reverse=reverse)
        # Prefer named outlets over Unknown when tied at zero
        for o in ranked:
            if getattr(o, key) or o.outlet not in {"Unknown", "Outlet Not Mapped"}:
                return o.outlet
        return ranked[0].outlet if ranked else None

    with_sales = [o for o in outlets if o.sales > 0]
    lowest = (
        min(with_sales, key=lambda o: o.sales).outlet
        if with_sales
        else best("sales", reverse=False)
    )

    return TopPerformers(
        highest_online_sales_outlet=best("sales"),
        highest_orders_outlet=best("total_orders"),
        highest_average_order_value=best("average_order_value"),
        highest_recoverable_amount=best("recoverable_amount"),
        lowest_performing_outlet=lowest,
        most_cancelled_outlet=best("cancelled"),
    )
