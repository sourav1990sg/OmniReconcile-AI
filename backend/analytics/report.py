"""Chart data, KPI cards, export datasets, executive + dashboard flatten."""

from __future__ import annotations

from typing import Any, Mapping

from backend.analytics.aggregations import AggregationIndex, pct
from backend.analytics.models import (
    AnalyticsReport,
    ExecutiveSummary,
    FinancialSummary,
    KpiCard,
    OutletSummary,
    PlatformSummary,
)


def build_executive(
    index: AggregationIndex,
    *,
    pos_meta: Mapping[str, Any] | None,
    settle_meta: Mapping[str, Any] | None,
    status_counts: Mapping[str, int] | None,
) -> ExecutiveSummary:
    g = index.global_bucket
    pos_meta = pos_meta or {}
    settle_meta = settle_meta or {}
    status_counts = status_counts or {}

    total_pos = int(pos_meta.get("total_orders") or g.order_count)
    cancelled = int(pos_meta.get("cancelled_orders") or status_counts.get("CANCELLED", g.cancelled))
    eligible = int(pos_meta.get("eligible_orders") or max(total_pos - cancelled, 0))
    matched = len(index.matched_rows)
    settlement_orders = int(settle_meta.get("total_orders") or matched)

    pending = int(status_counts.get("PENDING", g.pending))
    not_recon = int(status_counts.get("NOT_RECONCILED", g.not_reconciled))

    return ExecutiveSummary(
        total_pos_orders=total_pos,
        cancelled_orders=cancelled,
        eligible_orders=eligible,
        matched_orders=matched,
        payment_match_orders=g.payment_match,
        agreement_verified_orders=g.agreement_verified,
        agreement_violations=g.agreement_violations,
        pending_orders=pending,
        not_reconciled_orders=not_recon,
        settlement_coverage_pct=pct(matched, eligible if eligible else total_pos),
        recoverable_amount=round(g.recoverable, 2),
        total_online_sales=round(g.sales, 2),
        gross_order_value=round(g.gross_order_value, 2),
        platform_payout=round(g.platform_payout, 2),
        total_settlement_orders=settlement_orders,
        financial_discrepancy_orders=int(
            status_counts.get("FINANCIAL_DISCREPANCY", g.financial_discrepancy)
        ),
        financially_reconciled_orders=int(
            status_counts.get("FINANCIALLY_RECONCILED", g.financially_reconciled)
            + status_counts.get("RECONCILED", 0)
        ),
    )


def build_kpi_cards(exec_sum: ExecutiveSummary, financial: FinancialSummary) -> list[KpiCard]:
    return [
        KpiCard(
            id="total_pos_orders",
            label="Total POS Orders",
            value=f"{exec_sum.total_pos_orders:,}",
            caption=f"{exec_sum.eligible_orders} eligible · {exec_sum.cancelled_orders} cancelled",
            tone="neutral",
        ),
        KpiCard(
            id="matched_orders",
            label="Matched Orders",
            value=f"{exec_sum.matched_orders:,}",
            caption=(
                f"{exec_sum.financially_reconciled_orders} financially reconciled · "
                f"{exec_sum.settlement_coverage_pct}% coverage"
            ),
            tone="neutral",
        ),
        KpiCard(
            id="financial_discrepancy",
            label="Financial Discrepancy",
            value=f"{exec_sum.financial_discrepancy_orders:,}",
            caption=f"{exec_sum.not_reconciled_orders} not reconciled · {exec_sum.pending_orders} pending",
            tone="warning",
        ),
        KpiCard(
            id="recoverable_amount",
            label="Recoverable Amount",
            value=f"₹{exec_sum.recoverable_amount:,.2f}",
            caption="Unexplained underpayments only",
            tone="success",
        ),
        KpiCard(
            id="agreement_coverage",
            label="Agreement Coverage",
            value=f"{exec_sum.agreement_verified_orders:,}",
            caption=(
                f"{exec_sum.payment_match_orders} payment match · "
                f"{exec_sum.agreement_violations} violations"
            ),
            tone="warning" if exec_sum.agreement_violations else "neutral",
        ),
        KpiCard(
            id="platform_payout",
            label="Platform Payout",
            value=f"₹{financial.net_platform_payout:,.2f}",
            caption=f"GOV ₹{financial.gross_order_value:,.2f} · Sales ₹{financial.total_pos_sales:,.2f}",
            tone="neutral",
        ),
    ]


def build_chart_data(
    platforms: list[PlatformSummary],
    outlets: list[OutletSummary],
    exec_sum: ExecutiveSummary,
) -> dict[str, Any]:
    return {
        "orders_by_platform": [
            {"platform": p.platform, "orders": p.order_count} for p in platforms
        ],
        "revenue_by_platform": [
            {"platform": p.platform, "revenue": p.sales} for p in platforms
        ],
        "orders_by_outlet": [
            {"outlet": o.outlet, "orders": o.total_orders} for o in outlets
        ],
        "revenue_by_outlet": [
            {"outlet": o.outlet, "revenue": o.sales} for o in outlets
        ],
        "commission_by_platform": [
            {"platform": p.platform, "commission": p.commission} for p in platforms
        ],
        "recoverable_by_outlet": [
            {"outlet": o.outlet, "recoverable": o.recoverable_amount}
            for o in outlets
            if o.recoverable_amount > 0
        ],
        "payment_match": {
            "payment_match_orders": exec_sum.payment_match_orders,
            "matched_orders": exec_sum.matched_orders,
            "pct": pct(exec_sum.payment_match_orders, exec_sum.matched_orders),
        },
        "agreement_verification": {
            "verified": exec_sum.agreement_verified_orders,
            "violations": exec_sum.agreement_violations,
            "matched_orders": exec_sum.matched_orders,
        },
    }


def build_export_data(report: AnalyticsReport) -> dict[str, Any]:
    """Reusable datasets for Dashboard / PDF / Excel / Power BI / Mobile."""
    return {
        "dashboard": report.dashboard,
        "executive_summary": report.executive_summary.to_dict(),
        "platform_summary": [p.to_dict() for p in report.platform_summary],
        "outlet_summary": [o.to_dict() for o in report.outlet_summary],
        "financial_summary": report.financial_summary.to_dict(),
        "platform_comparison": report.platform_comparison.to_dict(),
        "top_performers": report.top_performers.to_dict(),
        "business_insights": list(report.business_insights),
        "kpi_cards": [c.to_dict() for c in report.kpi_cards],
        "chart_data": report.chart_data,
        "trends": report.trend_metrics.to_dict(),
    }


def flatten_dashboard(
    exec_sum: ExecutiveSummary,
    *,
    recon_totals: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Backward-compatible dashboard dict for existing FE / APIs.

    All values originate from AnalyticsReport executive summary (single source).
    """
    recon_totals = recon_totals or {}
    return {
        "total_pos_orders": exec_sum.total_pos_orders,
        "cancelled_orders": exec_sum.cancelled_orders,
        "eligible_orders": exec_sum.eligible_orders,
        "total_settlement_orders": exec_sum.total_settlement_orders,
        "matched_orders": exec_sum.matched_orders,
        "unmatched_orders": exec_sum.not_reconciled_orders + exec_sum.pending_orders,
        "unmatched_settlement": int(recon_totals.get("unmatched_settlement", 0)),
        "amount_mismatch": exec_sum.financial_discrepancy_orders,
        "financial_discrepancy": exec_sum.financial_discrepancy_orders,
        "pending": exec_sum.pending_orders,
        "not_reconciled": exec_sum.not_reconciled_orders,
        "reconciled": exec_sum.financially_reconciled_orders,
        "financially_reconciled": exec_sum.financially_reconciled_orders,
        "duplicate_settlement": int(recon_totals.get("duplicate_settlement", 0)),
        "manual_review": int(recon_totals.get("manual_review", 0)),
        "recoverable_amount": exec_sum.recoverable_amount,
        "total_expected": float(recon_totals.get("total_expected", exec_sum.platform_payout)),
        "total_settled": float(recon_totals.get("total_settled", exec_sum.platform_payout)),
        "total_difference": float(recon_totals.get("total_difference", 0.0)),
        "orders_verified_by_agreement": exec_sum.agreement_verified_orders,
        "orders_verified_by_settlement": max(
            exec_sum.payment_match_orders - exec_sum.agreement_verified_orders, 0
        ),
        "agreement_violations": exec_sum.agreement_violations,
        "unknown_agreement_terms": int(recon_totals.get("unknown_agreement_terms", 0)),
        "agreement_coverage": {
            "orders_verified_by_agreement": exec_sum.agreement_verified_orders,
            "orders_verified_by_settlement": max(
                exec_sum.payment_match_orders - exec_sum.agreement_verified_orders, 0
            ),
            "agreement_violations": exec_sum.agreement_violations,
            "unknown_agreement_terms": int(recon_totals.get("unknown_agreement_terms", 0)),
            "agreement_available": bool(recon_totals.get("agreement_available", False)),
        },
        "settlement_coverage_pct": exec_sum.settlement_coverage_pct,
        "total_online_sales": exec_sum.total_online_sales,
        "gross_order_value": exec_sum.gross_order_value,
        "platform_payout": exec_sum.platform_payout,
        "payment_match_orders": exec_sum.payment_match_orders,
    }
