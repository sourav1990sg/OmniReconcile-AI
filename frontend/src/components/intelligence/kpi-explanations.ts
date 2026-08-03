/**
 * KPI explainability catalog — formulas reference AnalyticsReport fields only.
 * No recalculation of business KPIs; display provenance for trust.
 */

export interface KpiExplanation {
  id: string;
  title: string;
  formula: string;
  description: string;
  sourceFields: string[];
  notes?: string;
}

export const KPI_EXPLANATIONS: Record<string, KpiExplanation> = {
  total_online_sales: {
    id: "total_online_sales",
    title: "Total Online Sales",
    formula: "Σ POS Sale for matched orders",
    description: "Sum of Petpooja POS ‘My Amount’ on orders that matched a settlement row.",
    sourceFields: ["executive_summary.total_online_sales", "platform_summary[].sales"],
  },
  platform_payout: {
    id: "platform_payout",
    title: "Platform Payout",
    formula: "Σ Actual Payout (settlement net payable)",
    description: "Sum of platform settlement payouts on matched orders.",
    sourceFields: ["executive_summary.platform_payout", "financial_summary.net_platform_payout"],
  },
  gross_order_value: {
    id: "gross_order_value",
    title: "Gross Order Value",
    formula: "Σ Gross Order Value from settlement financial breakdown",
    description: "Platform-reported GOV before commission and statutory deductions.",
    sourceFields: ["executive_summary.gross_order_value", "financial_summary.gross_order_value"],
  },
  recoverable: {
    id: "recoverable",
    title: "Recoverable Amount",
    formula: "Σ max(0, Calculated Payout − Actual Payout) where Status = FINANCIAL_DISCREPANCY",
    description:
      "Unexplained underpayments only. Cancelled / pending rows are excluded from recoverable.",
    sourceFields: [
      "executive_summary.recoverable_amount",
      "financial_summary.recoverable",
      "executive_summary.financial_discrepancy_orders",
    ],
  },
  aov: {
    id: "aov",
    title: "Average Order Value",
    formula: "Online Sales ÷ Matched Orders (per outlet or platform)",
    description: "Average POS sale per matched order in the selected slice.",
    sourceFields: ["outlet_summary[].average_order_value", "platform_summary[].average_order_value"],
  },
  settlement_coverage: {
    id: "settlement_coverage",
    title: "Settlement Coverage",
    formula: "Matched Orders ÷ Eligible POS Orders × 100",
    description:
      "Share of eligible POS orders that have a settlement counterpart. Cancelled orders are excluded from the denominator where AnalyticsReport defines eligible_orders.",
    sourceFields: [
      "executive_summary.settlement_coverage_pct",
      "executive_summary.matched_orders",
      "executive_summary.eligible_orders",
      "executive_summary.pending_orders",
      "executive_summary.cancelled_orders",
    ],
  },
  payment_match: {
    id: "payment_match",
    title: "Payment Match %",
    formula: "Payment Match Orders ÷ Matched Orders × 100",
    description:
      "Orders whose verification level is SETTLEMENT_VERIFIED or AGREEMENT_VERIFIED (or display Payment Match).",
    sourceFields: [
      "executive_summary.payment_match_orders",
      "executive_summary.matched_orders",
      "platform_summary[].payment_match_pct",
    ],
  },
  agreement_coverage: {
    id: "agreement_coverage",
    title: "Agreement Coverage",
    formula: "Agreement Verified Orders (count) / Agreement Violations (count)",
    description:
      "Commercial agreement verification results from Sprint 6B. Optional when no agreement is uploaded.",
    sourceFields: [
      "executive_summary.agreement_verified_orders",
      "executive_summary.agreement_violations",
      "platform_summary[].agreement_verification_pct",
    ],
  },
  commission: {
    id: "commission",
    title: "Commission",
    formula: "Σ settlement commission components",
    description: "Total platform commission deducted across matched settlements.",
    sourceFields: ["financial_summary.total_commission", "platform_summary[].commission"],
  },
  orders: {
    id: "orders",
    title: "Orders",
    formula: "Count of orders in slice (matched unless noted)",
    description: "Order counts from AnalyticsReport aggregations — never recomputed in the UI.",
    sourceFields: ["executive_summary.matched_orders", "platform_summary[].order_count"],
  },
};
