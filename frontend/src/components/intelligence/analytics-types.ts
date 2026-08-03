/**
 * AnalyticsReport types — mirrors backend/analytics/models.py.
 * Frontend must only render these values; never recompute KPIs.
 */

export type Tone = "neutral" | "warning" | "success";

export interface ExecutiveSummary {
  total_pos_orders: number;
  cancelled_orders: number;
  eligible_orders: number;
  matched_orders: number;
  payment_match_orders: number;
  agreement_verified_orders: number;
  agreement_violations: number;
  pending_orders: number;
  not_reconciled_orders: number;
  settlement_coverage_pct: number;
  recoverable_amount: number;
  total_online_sales: number;
  gross_order_value: number;
  platform_payout: number;
  total_settlement_orders: number;
  financial_discrepancy_orders: number;
  financially_reconciled_orders: number;
}

export interface PlatformSummary {
  platform: string;
  order_count: number;
  sales: number;
  gross_order_value: number;
  platform_payout: number;
  average_order_value: number;
  commission: number;
  government_charges: number;
  tds: number;
  tcs: number;
  gst: number;
  restaurant_discount: number;
  platform_discount: number;
  promo_recovery: number;
  customer_compensation: number;
  other_deductions: number;
  net_deductions: number;
  recoverable_amount: number;
  settlement_coverage_pct: number;
  payment_match_pct: number;
  agreement_verification_pct: number;
  payment_match_orders: number;
  agreement_verified_orders: number;
}

export interface OutletSummary {
  outlet: string;
  swiggy_orders: number;
  zomato_orders: number;
  total_orders: number;
  sales: number;
  gross_order_value: number;
  platform_payout: number;
  average_order_value: number;
  commission: number;
  recoverable_amount: number;
  payment_match_pct: number;
  agreement_verified_pct: number;
  cancelled: number;
  pending: number;
  platform_wise_orders: Record<string, number>;
}

export interface TopPerformers {
  highest_online_sales_outlet: string | null;
  highest_orders_outlet: string | null;
  highest_average_order_value: string | null;
  highest_recoverable_amount: string | null;
  lowest_performing_outlet: string | null;
  most_cancelled_outlet: string | null;
}

export interface FinancialSummary {
  total_pos_sales: number;
  gross_order_value: number;
  total_commission: number;
  total_payment_fees: number;
  total_gst: number;
  total_government_charges: number;
  total_tcs: number;
  total_tds: number;
  total_platform_deductions: number;
  total_promo_recovery: number;
  total_customer_compensation: number;
  net_platform_payout: number;
  recoverable: number;
}

export interface PlatformComparison {
  swiggy_order_share_pct: number;
  zomato_order_share_pct: number;
  swiggy_revenue_share_pct: number;
  zomato_revenue_share_pct: number;
  swiggy_payout_share_pct: number;
  zomato_payout_share_pct: number;
  swiggy_commission_pct: number;
  zomato_commission_pct: number;
  swiggy_aov: number;
  zomato_aov: number;
}

export interface KpiCard {
  id?: string;
  label: string;
  value: string;
  caption: string;
  tone?: Tone | string;
}

export interface ChartData {
  orders_by_platform?: Array<{ platform: string; orders: number }>;
  revenue_by_platform?: Array<{ platform: string; revenue: number }>;
  orders_by_outlet?: Array<{ outlet: string; orders: number }>;
  revenue_by_outlet?: Array<{ outlet: string; revenue: number }>;
  commission_by_platform?: Array<{ platform: string; commission: number }>;
  recoverable_by_outlet?: Array<{ outlet: string; recoverable: number }>;
  payment_match?: { payment_match_orders: number; matched_orders: number; pct: number };
  agreement_verification?: {
    verified: number;
    violations: number;
    matched_orders: number;
  };
}

export interface AnalyticsReport {
  executive_summary: ExecutiveSummary;
  platform_summary: PlatformSummary[];
  outlet_summary: OutletSummary[];
  top_performers: TopPerformers;
  financial_summary: FinancialSummary;
  platform_comparison: PlatformComparison;
  business_insights: string[];
  trend_metrics?: {
    orders_by_day?: Array<{ date: string; orders: number }>;
    sales_by_day?: Array<{ date: string; sales: number }>;
    payout_by_day?: Array<{ date: string; payout: number }>;
  };
  kpi_cards: KpiCard[];
  chart_data: ChartData;
  export_data?: Record<string, unknown>;
  dashboard?: Record<string, unknown>;
}

export interface AgreementSummaryView {
  count?: number;
  active?: {
    agreement_id?: string;
    version?: string;
    status?: string;
    platform?: string;
    restaurant?: string;
    source_filename?: string;
    unknown_terms?: number;
    effective_from?: string | null;
    effective_to?: string | null;
    rules?: Record<string, { value?: unknown; unknown?: boolean; confidence?: number }>;
  } | null;
  agreements?: Array<Record<string, unknown>>;
}

/** Display-only money formatter (no business math). */
export function formatInr(value: number | undefined | null): string {
  const n = Number(value ?? 0);
  return `₹${Math.abs(n).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatPct(value: number | undefined | null): string {
  return `${Number(value ?? 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  })}%`;
}

export function formatInt(value: number | undefined | null): string {
  return Number(value ?? 0).toLocaleString("en-IN");
}
