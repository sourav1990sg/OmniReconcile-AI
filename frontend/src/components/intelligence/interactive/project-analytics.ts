/**
 * Slice AnalyticsReport for display filters — SELECT only, never recompute KPIs.
 * Values always come from existing AnalyticsReport fields / nested arrays.
 */

import type {
  AnalyticsReport,
  ChartData,
  ExecutiveSummary,
  FinancialSummary,
  OutletSummary,
  PlatformSummary,
} from "@/components/intelligence/analytics-types";
import type { BiFilterState } from "@/components/intelligence/interactive/filter-types";

export interface AnalyticsViewModel {
  /** Full unfiltered report (source of truth). */
  source: AnalyticsReport;
  /** Platform rows visible under current platform filter. */
  platforms: PlatformSummary[];
  /** Outlet rows visible under current outlet filter. */
  outlets: OutletSummary[];
  /** Chart series sliced to selected platform/outlet keys. */
  chart_data: ChartData;
  /**
   * Hero metrics for tiles — when a single platform is selected, values are
   * READ from that PlatformSummary; when a single outlet is selected, from
   * OutletSummary; otherwise from executive_summary. No arithmetic aggregation.
   */
  hero: {
    online_sales: number;
    platform_payout: number;
    recoverable: number;
    settlement_coverage_pct: number;
    orders: number;
    aov: number;
    gross_order_value: number;
    commission: number;
    payment_match_pct: number;
    agreement_verification_pct: number;
    source_label: string;
  };
  executive: ExecutiveSummary;
  financial: FinancialSummary;
  filterActive: boolean;
}

function filterChartData(chart: ChartData, f: BiFilterState): ChartData {
  const plat = f.platform;
  const outlet = f.outlet;
  const matchPlat = (name: string) => plat === "All" || name === plat;
  const matchOut = (name: string) => outlet === "All" || name === outlet;

  const next: ChartData = {
    orders_by_platform: (chart.orders_by_platform ?? []).filter((d) => matchPlat(d.platform)),
    revenue_by_platform: (chart.revenue_by_platform ?? []).filter((d) => matchPlat(d.platform)),
    commission_by_platform: (chart.commission_by_platform ?? []).filter((d) =>
      matchPlat(d.platform),
    ),
    orders_by_outlet: (chart.orders_by_outlet ?? []).filter((d) => matchOut(d.outlet)),
    revenue_by_outlet: (chart.revenue_by_outlet ?? []).filter((d) => matchOut(d.outlet)),
    recoverable_by_outlet: (chart.recoverable_by_outlet ?? []).filter((d) => matchOut(d.outlet)),
  };
  if (chart.payment_match) next.payment_match = chart.payment_match;
  if (chart.agreement_verification) next.agreement_verification = chart.agreement_verification;
  return next;
}

function buildHero(
  report: AnalyticsReport,
  platforms: PlatformSummary[],
  outlets: OutletSummary[],
  f: BiFilterState,
): AnalyticsViewModel["hero"] {
  const ex = report.executive_summary;

  if (f.platform !== "All" && platforms.length === 1) {
    const p = platforms[0]!;
    return {
      online_sales: p.sales,
      platform_payout: p.platform_payout,
      recoverable: p.recoverable_amount,
      settlement_coverage_pct: p.settlement_coverage_pct,
      orders: p.order_count,
      aov: p.average_order_value,
      gross_order_value: p.gross_order_value,
      commission: p.commission,
      payment_match_pct: p.payment_match_pct,
      agreement_verification_pct: p.agreement_verification_pct,
      source_label: `PlatformSummary · ${p.platform}`,
    };
  }

  if (f.outlet !== "All" && outlets.length === 1) {
    const o = outlets[0]!;
    return {
      online_sales: o.sales,
      platform_payout: o.platform_payout,
      recoverable: o.recoverable_amount,
      settlement_coverage_pct: report.executive_summary.settlement_coverage_pct,
      orders: o.total_orders,
      aov: o.average_order_value,
      gross_order_value: o.gross_order_value,
      commission: o.commission,
      payment_match_pct: o.payment_match_pct,
      agreement_verification_pct: o.agreement_verified_pct,
      source_label: `OutletSummary · ${o.outlet} (coverage from executive_summary)`,
    };
  }

  return {
    online_sales: ex.total_online_sales,
    platform_payout: ex.platform_payout,
    recoverable: ex.recoverable_amount,
    settlement_coverage_pct: ex.settlement_coverage_pct,
    orders: ex.matched_orders,
    aov:
      report.outlet_summary.find((o) => o.outlet === report.top_performers.highest_average_order_value)
        ?.average_order_value ?? 0,
    gross_order_value: ex.gross_order_value,
    commission: report.financial_summary.total_commission,
    payment_match_pct: report.chart_data.payment_match?.pct ?? 0,
    agreement_verification_pct: 0,
    source_label: "executive_summary",
  };
}

/** Pure view projection — no KPI math beyond selecting report fields. */
export function projectAnalyticsView(
  report: AnalyticsReport,
  filters: BiFilterState,
): AnalyticsViewModel {
  const platforms =
    filters.platform === "All"
      ? report.platform_summary
      : report.platform_summary.filter((p) => p.platform === filters.platform);

  const outlets =
    filters.outlet === "All"
      ? report.outlet_summary
      : report.outlet_summary.filter((o) => o.outlet === filters.outlet);

  const filterActive =
    filters.platform !== "All" ||
    filters.outlet !== "All" ||
    filters.period !== "all" ||
    Boolean(filters.dateFrom || filters.dateTo);

  return {
    source: report,
    platforms,
    outlets,
    chart_data: filterChartData(report.chart_data, filters),
    hero: buildHero(report, platforms, outlets, filters),
    executive: report.executive_summary,
    financial: report.financial_summary,
    filterActive,
  };
}
